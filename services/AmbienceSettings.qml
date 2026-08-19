import Quickshell
import Quickshell.Io
import QtQuick
import "EffectRegistry.js" as EffectRegistry

// Sole owner of the standalone settings document. Consumers receive only the
// normalized data/projections below and never read the file themselves.
QtObject {
  id: root

  signal loaded()

  readonly property int schemaVersion: 1
  readonly property string configHome: resolveBasePath("XDG_CONFIG_HOME", "/.config")
  readonly property string settingsDir: configHome !== ""
    ? configHome + "/omarchy/jobo/desktop-ambience" : ""
  readonly property string settingsFile: settingsDir !== "" ? settingsDir + "/settings.json" : ""
  readonly property bool pathReady: settingsDir !== "" && settingsFile !== ""

  property var data: defaultData()
  property var lastValidData: defaultData()
  property var pendingSave: null
  property bool directoryReady: false
  property bool directoryFailed: false
  property bool hasLoaded: false
  property bool diskDiverged: false
  property bool recoveredFromMalformedEdit: false
  property string loadError: ""

  property string queuedSavePayload: ""
  property int queuedSaveRevision: 0
  property string inFlightSavePayload: ""
  property int inFlightSaveRevision: 0
  property string lastConfirmedSavePayload: ""
  property string retrySavePayload: ""
  property int retrySaveRevision: 0
  property int retryWriteNonce: 0
  property bool writeInFlight: false
  property int requestedSaveRevision: 0
  property int confirmedSaveRevision: 0
  property string persistenceState: "idle"
  property string persistenceError: ""
  property int suppressFileReloads: 0

  readonly property bool persistenceReady: directoryReady && hasLoaded
  readonly property bool retryAvailable: directoryFailed || retrySavePayload !== ""
  readonly property bool enabled: data.enabled !== false
  readonly property string presentation: data.presentation === "foreground" ? "foreground" : "background"
  readonly property real opacity: Number(data.opacity)
  readonly property bool reduceMotion: data.reduceMotion === true
  readonly property var activeEffects: data.activeEffects || []
  readonly property var effects: data.effects || ({})
  readonly property var backgroundVignette: data.backgroundVignette || ({})

  function isAbsolutePath(value) {
    var path = String(value || "").trim()
    return path.length > 1 && path.charAt(0) === "/"
  }

  function resolveBasePath(environmentName, homeSuffix) {
    var explicitPath = String(Quickshell.env(environmentName) || "").trim()
    if (explicitPath !== "") return isAbsolutePath(explicitPath) ? explicitPath : ""
    var home = String(Quickshell.env("HOME") || "").trim()
    return isAbsolutePath(home) ? home + homeSuffix : ""
  }

  function defineOwn(target, key, value) {
    Object.defineProperty(target, String(key), {
      value: value, enumerable: true, writable: true, configurable: true
    })
  }

  function defaultData() {
    return {
      version: root.schemaVersion,
      enabled: true,
      presentation: "background",
      opacity: 1,
      reduceMotion: false,
      activeEffects: ["trackingLines"],
      effects: EffectRegistry.defaultEffects(),
      backgroundVignette: EffectRegistry.vignetteDefaults()
    }
  }

  function normalizeJsonValue(value) {
    if (value === null || typeof value === "string" || typeof value === "boolean") return value
    if (typeof value === "number") return isFinite(value) ? value : undefined
    if (Array.isArray(value)) {
      var array = []
      for (var i = 0; i < value.length; i++) {
        var item = normalizeJsonValue(value[i])
        if (item !== undefined) array.push(item)
      }
      return array
    }
    if (value && typeof value === "object") {
      var object = {}
      var keys = Object.keys(value)
      for (var j = 0; j < keys.length; j++) {
        var key = keys[j]
        var child = normalizeJsonValue(value[key])
        if (child !== undefined) defineOwn(object, key, child)
      }
      return object
    }
    return undefined
  }

  function preserveUnknownJson(target, source, knownKeys) {
    if (!target || !source || typeof source !== "object" || Array.isArray(source)) return
    var keys = Object.keys(source)
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i]
      if (knownKeys && Object.prototype.hasOwnProperty.call(knownKeys, key)
          && knownKeys[key] === true) continue
      var safe = normalizeJsonValue(source[key])
      if (safe !== undefined) defineOwn(target, key, safe)
    }
  }

  function boundedReal(value, fallback, minimum, maximum) {
    var parsed = Number(value)
    if (!isFinite(parsed)) return fallback
    return Math.max(minimum, Math.min(maximum, parsed))
  }

  function normalizeActiveEffects(value) {
    var values = Array.isArray(value) ? value : defaultData().activeEffects
    var result = []
    var seen = Object.create(null)
    for (var i = 0; i < values.length; i++) {
      var effectId = String(values[i] || "").trim()
      if (!EffectRegistry.isOrderedId(effectId) || seen[effectId] === true) continue
      seen[effectId] = true
      result.push(effectId)
    }
    return result
  }

  function normalizeEffect(effectId, value) {
    var source = value
    if (value === true || value === false) source = { enabled: value === true }
    source = source && typeof source === "object" && !Array.isArray(source) ? source : ({})
    var next = EffectRegistry.normalizeEffect(effectId, source)
    preserveUnknownJson(next, source, EffectRegistry.knownEffectKeys(effectId))
    return next
  }

  function normalizeVignette(value) {
    var source = value
    if (value === true || value === false) source = { enabled: value === true }
    source = source && typeof source === "object" && !Array.isArray(source) ? source : ({})
    var next = EffectRegistry.normalizeVignette(source)
    preserveUnknownJson(next, source, EffectRegistry.knownVignetteKeys())
    return next
  }

  function normalize(value) {
    var source = value && typeof value === "object" && !Array.isArray(value) ? value : ({})
    var next = defaultData()
    next.enabled = source.enabled !== false
    next.presentation = String(source.presentation || "") === "foreground" ? "foreground" : "background"
    next.opacity = boundedReal(source.opacity, 1, 0, 1)
    next.reduceMotion = source.reduceMotion === true
    next.activeEffects = normalizeActiveEffects(source.activeEffects)

    var sourceEffects = source.effects && typeof source.effects === "object"
      && !Array.isArray(source.effects) ? source.effects : ({})
    var ids = EffectRegistry.orderedIds()
    var knownIds = Object.create(null)
    next.effects = {}
    for (var i = 0; i < ids.length; i++) {
      var effectId = ids[i]
      knownIds[effectId] = true
      defineOwn(next.effects, effectId, normalizeEffect(effectId, sourceEffects[effectId]))
    }
    // Keep future effect payloads round-trippable without making unknown IDs
    // renderable. Historical aliases and the dedicated vignette are reserved.
    var sourceEffectIds = Object.keys(sourceEffects)
    for (var j = 0; j < sourceEffectIds.length; j++) {
      var sourceEffectId = sourceEffectIds[j]
      if (knownIds[sourceEffectId] === true
          || sourceEffectId === "vhs"
          || sourceEffectId === "backgroundVignette") continue
      var safeEffect = normalizeJsonValue(sourceEffects[sourceEffectId])
      if (safeEffect !== undefined) defineOwn(next.effects, sourceEffectId, safeEffect)
    }
    next.backgroundVignette = normalizeVignette(source.backgroundVignette)

    preserveUnknownJson(next, source, {
      version: true,
      enabled: true,
      presentation: true,
      opacity: true,
      reduceMotion: true,
      activeEffects: true,
      effects: true,
      backgroundVignette: true
    })
    next.version = root.schemaVersion
    return next
  }

  function load() {
    if (!pathReady) {
      failInvalidPath()
      return
    }
    if (!directoryReady) {
      ensureSettingsDirectory()
      return
    }
    settingsFileView.reload()
  }

  function applyLoadedText(raw) {
    var parsed
    var validDiskDocument = false
    try {
      var text = String(raw === undefined || raw === null ? "" : raw)
      if (text.trim() === "") throw new Error("settings file is empty")
      var decoded = JSON.parse(text)
      if (!decoded || typeof decoded !== "object" || Array.isArray(decoded))
        throw new Error("settings root must be an object")
      parsed = normalize(decoded)
      validDiskDocument = true
      loadError = ""
      recoveredFromMalformedEdit = false
      diskDiverged = false
    } catch (error) {
      // The in-memory default is already valid before first load. After any
      // valid/default state is established, malformed external edits never
      // replace it or transiently unmap effects.
      loadError = "Settings file is not valid JSON (" + String(error) + ")"
      recoveredFromMalformedEdit = true
      diskDiverged = true
      parsed = hasLoaded ? lastValidData : normalize(data)
    }

    data = parsed
    lastValidData = normalize(parsed)
    if (validDiskDocument && !writeInFlight)
      lastConfirmedSavePayload = JSON.stringify(data, null, 2) + "\n"
    hasLoaded = true
    if (persistenceState === "retrying") {
      persistenceState = "saved"
      persistenceError = ""
    }
    Qt.callLater(root.finishLoad)
  }

  function applyMissingFile() {
    // A missing first-run file establishes usable in-memory defaults, not a
    // false disk confirmation. The next save therefore creates the document.
    data = normalize(data)
    lastValidData = normalize(data)
    lastConfirmedSavePayload = ""
    diskDiverged = true
    loadError = ""
    recoveredFromMalformedEdit = false
    hasLoaded = true
    if (persistenceState === "retrying") {
      persistenceState = "idle"
      persistenceError = ""
    }
    Qt.callLater(root.finishLoad)
  }

  function finishLoad() {
    resolvePendingSave()
    loaded()
  }

  function resolvePendingSave() {
    if (pendingSave === null) return
    var queued = pendingSave
    pendingSave = null
    save(queued)
  }

  function forcedWriteText(payload) {
    retryWriteNonce += 1
    var text = payload
    for (var i = 0; i < retryWriteNonce; i++) text += "\n"
    return text
  }

  function writePayload(payload, revision, forceWrite) {
    var nextRevision = Math.max(1, Number(revision) || 0)
    if (writeInFlight) {
      if (payload === inFlightSavePayload) {
        inFlightSaveRevision = nextRevision
        queuedSavePayload = ""
        queuedSaveRevision = 0
      } else {
        queuedSavePayload = payload
        queuedSaveRevision = nextRevision
      }
      persistenceState = "saving"
      return
    }

    if (!directoryReady) {
      queuedSavePayload = payload
      queuedSaveRevision = nextRevision
      ensureSettingsDirectory()
      return
    }

    writeInFlight = true
    inFlightSavePayload = payload
    inFlightSaveRevision = nextRevision
    persistenceState = persistenceState === "retrying" ? "retrying" : "saving"
    persistenceError = ""
    suppressFileReloads += 1
    settingsFileView.setText(forceWrite === true ? forcedWriteText(payload) : payload)
  }

  function handleSaveSucceeded() {
    if (!writeInFlight) return
    Qt.callLater(function() {
      if (root.suppressFileReloads > 0) root.suppressFileReloads -= 1
    })
    confirmedSaveRevision = Math.max(confirmedSaveRevision, inFlightSaveRevision)
    lastConfirmedSavePayload = inFlightSavePayload
    diskDiverged = false
    retrySavePayload = ""
    retrySaveRevision = 0
    writeInFlight = false
    inFlightSavePayload = ""
    inFlightSaveRevision = 0

    if (queuedSavePayload !== "") {
      var nextPayload = queuedSavePayload
      var nextRevision = queuedSaveRevision
      queuedSavePayload = ""
      queuedSaveRevision = 0
      persistenceState = "saving"
      writePayload(nextPayload, nextRevision)
    } else {
      persistenceState = "saved"
      persistenceError = ""
      retryWriteNonce = 0
    }
  }

  function handleSaveFailed(error) {
    if (!writeInFlight) return
    suppressFileReloads = Math.max(0, suppressFileReloads - 1)
    var failedPayload = inFlightSavePayload
    var failedRevision = inFlightSaveRevision
    writeInFlight = false
    inFlightSavePayload = ""
    inFlightSaveRevision = 0

    if (queuedSavePayload !== "") {
      var nextPayload = queuedSavePayload
      var nextRevision = queuedSaveRevision
      queuedSavePayload = ""
      queuedSaveRevision = 0
      persistenceState = "saving"
      writePayload(nextPayload, nextRevision)
      return
    }

    retrySavePayload = failedPayload
    retrySaveRevision = failedRevision
    persistenceState = "failed"
    persistenceError = "Could not save desktop ambience settings (" + String(error) + ")"
  }

  function retryPersistence() {
    if (writeInFlight) return false
    if (directoryFailed) {
      directoryFailed = false
      persistenceState = "retrying"
      persistenceError = ""
      ensureSettingsDirectory()
      return true
    }
    if (retrySavePayload === "") return false
    writeInFlight = true
    inFlightSavePayload = retrySavePayload
    inFlightSaveRevision = retrySaveRevision || requestedSaveRevision
    persistenceState = "retrying"
    persistenceError = ""
    suppressFileReloads += 1
    settingsFileView.setText(forcedWriteText(retrySavePayload))
    return true
  }

  function clearSupersededRetry() {
    retrySavePayload = ""
    retrySaveRevision = 0
    retryWriteNonce = 0
  }

  function save(next) {
    var normalized = normalize(next)
    data = normalized
    lastValidData = normalize(normalized)

    if (!hasLoaded) {
      pendingSave = normalized
      load()
      return
    }

    var json = JSON.stringify(normalized, null, 2) + "\n"
    requestedSaveRevision += 1
    // Every explicit save is a newer intent, even when it resolves to bytes
    // already confirmed on disk. A failed older payload must not stay retryable.
    var forceWrite = retrySavePayload !== "" && json === retrySavePayload
    clearSupersededRetry()
    if (!writeInFlight && !diskDiverged && json === lastConfirmedSavePayload) {
      confirmedSaveRevision = requestedSaveRevision
      persistenceState = "saved"
      persistenceError = ""
      return
    }
    writePayload(json, requestedSaveRevision, forceWrite)
  }

  function failInvalidPath() {
    directoryReady = false
    directoryFailed = true
    persistenceState = "failed"
    persistenceError = "Desktop ambience settings require an absolute XDG_CONFIG_HOME or HOME"
  }

  function ensureSettingsDirectory() {
    if (!pathReady) {
      failInvalidPath()
      return
    }
    if (directoryReady || ensureDirectoryProcess.running) return
    ensureDirectoryProcess.command = ["mkdir", "-p", root.settingsDir]
    ensureDirectoryProcess.running = true
  }

  Component.onCompleted: ensureSettingsDirectory()

  property Process ensureDirectoryProcess: Process {
    id: ensureDirectoryProcess
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.directoryFailed = true
        root.persistenceState = "failed"
        root.persistenceError = "Could not create desktop ambience settings directory"
        return
      }
      root.directoryFailed = false
      root.directoryReady = true
      // Changing the path attaches and loads the watcher. A delayed fallback
      // avoids racing that implicit load with an explicit reload.
      root.initialLoadFallback.restart()
    }
  }

  property Timer initialLoadFallback: Timer {
    id: initialLoadFallback
    interval: 80
    repeat: false
    onTriggered: if (root.directoryReady && !root.hasLoaded) settingsFileView.reload()
  }

  property FileView settingsFileView: FileView {
    id: settingsFileView
    path: root.directoryReady && root.pathReady ? root.settingsFile : ""
    watchChanges: true
    atomicWrites: true
    printErrors: false
    onLoaded: root.applyLoadedText(text())
    onSaved: root.handleSaveSucceeded()
    onSaveFailed: function(error) { root.handleSaveFailed(error) }
    onFileChanged: {
      if (root.suppressFileReloads > 0) root.suppressFileReloads -= 1
      else reload()
    }
    onLoadFailed: {
      if (!root.directoryReady || !root.pathReady) return
      if (!root.hasLoaded) root.applyMissingFile()
      else {
        root.diskDiverged = true
        root.loadError = "Settings file could not be read"
      }
    }
  }
}
