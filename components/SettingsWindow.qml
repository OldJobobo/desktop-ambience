import Quickshell
import QtQuick
import QtQuick.Controls as QQC
import qs.Commons
import qs.Ui
import "../services/EffectRegistry.js" as EffectRegistry
import "../services/LauncherIcons.js" as LauncherIcons

// Standalone Animations settings surface. It owns no persistence itself: every
// interaction mutates a normalized copy through AmbienceSettings.
Item {
  id: root

  property var settings: null
  property var shell: null
  property string pluginId: "jobo.desktop-ambience"
  property bool closingFromHost: false
  property bool closeReportingReady: false
  property string selectedEffectId: "trackingLines"
  property bool resetArmed: false
  readonly property bool opened: window.visible
  readonly property var windowObject: window
  readonly property var contentObject: focusScope
  readonly property var activeOrder: settings && settings.data && Array.isArray(settings.data.activeEffects)
    ? settings.data.activeEffects : []
  readonly property var effectDefinitions: EffectRegistry.orderedDefinitions()
  readonly property var launcherIcons: LauncherIcons.definitions()
  readonly property string barIconId: barIconFromShell()
  readonly property color muted: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.58)
  readonly property color faint: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.09)
  readonly property color accentWash: Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.14)

  readonly property QtObject controlPalette: QtObject {
    readonly property color foreground: Color.foreground
    readonly property color background: Color.background
  }

  function open(payloadJson) {
    var payload = {}
    try { payload = JSON.parse(String(payloadJson || "{}")) || {} } catch (error) {}
    if (EffectRegistry.isOrderedId(payload.effect)) selectedEffectId = String(payload.effect)
    ensureSelection()
    window.visible = true
    Qt.callLater(function() { focusScope.forceActiveFocus() })
  }

  function close() {
    closingFromHost = true
    window.visible = false
    closingFromHost = false
    resetArmed = false
  }

  function requestClose() {
    if (shell && typeof shell.hide === "function") shell.hide(pluginId)
    else window.visible = false
  }

  function ensureSelection() {
    if (EffectRegistry.isOrderedId(selectedEffectId)) return
    selectedEffectId = activeOrder.length > 0 ? String(activeOrder[0]) : "trackingLines"
  }

  function normalizedDocument() {
    return settings && settings.normalize ? settings.normalize(settings.data) : null
  }

  function commit(next) {
    if (!next || !settings || !settings.save) return false
    settings.save(next)
    return true
  }

  function setEnabled(value) {
    var next = normalizedDocument()
    if (!next) return false
    next.enabled = value === true
    return commit(next)
  }

  function setPresentation(value) {
    var next = normalizedDocument()
    if (!next) return false
    next.presentation = String(value) === "foreground" ? "foreground" : "background"
    return commit(next)
  }

  function setOpacity(value) {
    var next = normalizedDocument()
    if (!next) return false
    next.opacity = Number(value)
    return commit(next)
  }

  function setReduceMotion(value) {
    var next = normalizedDocument()
    if (!next) return false
    next.reduceMotion = value === true
    return commit(next)
  }

  function barEntryId(entry) {
    return typeof entry === "string" ? entry : String(entry && entry.id || "")
  }

  function barIconFromShell() {
    var config = shell && shell.shellConfig ? shell.shellConfig : null
    var layout = config && config.bar ? config.bar.layout : null
    if (!layout) return LauncherIcons.DEFAULT_ID
    var sections = ["left", "center", "right"]
    for (var sectionIndex = 0; sectionIndex < sections.length; sectionIndex++) {
      var entries = layout[sections[sectionIndex]]
      if (!Array.isArray(entries)) continue
      for (var entryIndex = 0; entryIndex < entries.length; entryIndex++) {
        var entry = entries[entryIndex]
        if (barEntryId(entry) !== pluginId) continue
        var icon = entry && entry.icon !== undefined ? entry.icon
          : (entry && entry.settings ? entry.settings.icon : "")
        return LauncherIcons.normalize(icon)
      }
    }
    return LauncherIcons.DEFAULT_ID
  }

  function setBarIcon(iconId) {
    var normalized = LauncherIcons.normalize(iconId)
    if (!shell || typeof shell.mutateShellConfig !== "function") return false
    var changed = false
    shell.mutateShellConfig(function(config) {
      var layout = config && config.bar ? config.bar.layout : null
      if (!layout) return
      var sections = ["left", "center", "right"]
      for (var sectionIndex = 0; sectionIndex < sections.length; sectionIndex++) {
        var entries = layout[sections[sectionIndex]]
        if (!Array.isArray(entries)) continue
        for (var entryIndex = 0; entryIndex < entries.length; entryIndex++) {
          var entry = entries[entryIndex]
          if (barEntryId(entry) !== pluginId) continue
          if (typeof entry === "string") {
            entry = { id: pluginId }
            entries[entryIndex] = entry
          }
          if (entry.icon === normalized && !(entry.settings && entry.settings.icon)) return
          entry.icon = normalized
          // Migrate the short-lived nested shape written by plugin 0.3.0.
          if (entry.settings && entry.settings.icon !== undefined) {
            var remainingSettings = {}
            var hasRemainingSettings = false
            for (var key in entry.settings) {
              if (key === "icon") continue
              remainingSettings[key] = entry.settings[key]
              hasRemainingSettings = true
            }
            if (hasRemainingSettings) entry.settings = remainingSettings
            else delete entry.settings
          }
          changed = true
          return
        }
      }
    })
    return changed
  }

  function setVignetteField(key, value) {
    var definitions = EffectRegistry.vignetteFieldDefinitions()
    var known = false
    for (var i = 0; i < definitions.length; i++) if (definitions[i].key === key) known = true
    if (!known) return false
    var next = normalizedDocument()
    if (!next) return false
    next.backgroundVignette[key] = value
    if (key === "intensity") next.backgroundVignette.enabled = true
    return commit(next)
  }

  function effectIsActive(effectId) {
    return activeOrder.indexOf(String(effectId || "")) >= 0
  }

  function fieldsFor(effectId) {
    return EffectRegistry.fieldDefinitions(effectId)
  }

  function effectLabel(effectId) {
    var definition = EffectRegistry.definition(effectId)
    return definition ? definition.label : String(effectId || "")
  }

  function addEffect(effectId) {
    var id = String(effectId || "")
    if (!EffectRegistry.isOrderedId(id)) return false
    var next = normalizedDocument()
    if (!next) return false
    if (next.activeEffects.indexOf(id) < 0) next.activeEffects.push(id)
    next.effects[id].enabled = true
    next.enabled = true
    selectedEffectId = id
    return commit(next)
  }

  function removeEffect(effectId) {
    var id = String(effectId || "")
    var next = normalizedDocument()
    if (!next) return false
    var index = next.activeEffects.indexOf(id)
    if (index < 0) return false
    next.activeEffects.splice(index, 1)
    return commit(next)
  }

  function moveEffect(effectId, direction) {
    var id = String(effectId || "")
    var next = normalizedDocument()
    if (!next) return false
    var index = next.activeEffects.indexOf(id)
    var target = index + (Number(direction) < 0 ? -1 : 1)
    if (index < 0 || target < 0 || target >= next.activeEffects.length) return false
    next.activeEffects.splice(index, 1)
    next.activeEffects.splice(target, 0, id)
    return commit(next)
  }

  function setEffectField(effectId, key, value) {
    var id = String(effectId || "")
    var fields = EffectRegistry.fieldDefinitions(id)
    var known = false
    for (var i = 0; i < fields.length; i++) if (fields[i].key === key) known = true
    if (!known) return false
    var next = normalizedDocument()
    if (!next) return false
    next.effects[id][key] = value
    if (key !== "enabled") next.effects[id].enabled = true
    return commit(next)
  }

  function effectValue(effectId, key) {
    var effects = settings && settings.data && settings.data.effects ? settings.data.effects : ({})
    var effect = effects[String(effectId || "")] || ({})
    return effect[key]
  }

  function vignetteValue(key) {
    var vignette = settings && settings.data ? settings.data.backgroundVignette : null
    return vignette ? vignette[key] : undefined
  }

  function fieldValueText(field, value) {
    if (!field) return ""
    if (field.type === "int") {
      if (String(field.key).indexOf("Interval") >= 0) return (Number(value) / 1000).toFixed(1) + " s"
      return String(Math.round(Number(value)))
    }
    var numeric = Number(value)
    if (!isFinite(numeric)) return "—"
    if (field.minimum === 0 && field.maximum === 1) return Math.round(numeric * 100) + "%"
    return numeric.toFixed(field.step < 0.05 ? 2 : 1)
  }

  function persistenceName() {
    if (!settings) return "Loading"
    var state = String(settings.persistenceState || "idle")
    if (state === "saving") return "Saving"
    if (state === "retrying") return "Retrying"
    if (state === "failed") return "Save failed"
    if (state === "saved") return "Saved"
    return settings.persistenceReady ? "Ready" : "Loading"
  }

  function persistenceColor() {
    if (settings && settings.persistenceState === "failed") return Color.urgent
    if (settings && (settings.persistenceState === "saving" || settings.persistenceState === "retrying")) return Color.accent
    return Color.foreground
  }

  function retryPersistence() {
    return settings && settings.retryPersistence ? settings.retryPersistence() : false
  }

  function resetAll() {
    if (!settings || !settings.defaultData) return false
    selectedEffectId = "trackingLines"
    resetArmed = false
    setBarIcon(LauncherIcons.DEFAULT_ID)
    return commit(settings.defaultData())
  }

  function requestReset() {
    if (!resetArmed) {
      resetArmed = true
      resetTimer.restart()
      return
    }
    resetAll()
  }

  Component.onCompleted: Qt.callLater(function() { closeReportingReady = true })

  Connections {
    target: root.settings
    ignoreUnknownSignals: true
    function onLoaded() { root.ensureSelection() }
  }

  Timer {
    id: resetTimer
    interval: 5000
    onTriggered: root.resetArmed = false
  }

  FloatingWindow {
    id: window
    visible: false
    title: "Desktop Ambience"
    color: Color.background
    implicitWidth: 920
    implicitHeight: 760
    minimumSize: Qt.size(720, 560)

    onVisibleChanged: {
      if (!visible && root.closeReportingReady && !root.closingFromHost
          && root.shell && typeof root.shell.hide === "function")
        root.shell.hide(root.pluginId)
    }

    FocusScope {
      id: focusScope
      anchors.fill: parent
      focus: true
      Keys.onEscapePressed: root.requestClose()

      Column {
        id: windowLayout
        anchors.fill: parent
        anchors.margins: Style.space(18)
        spacing: Style.space(14)

        Item {
          width: parent.width
          height: Style.space(58)

          Column {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(3)

            Text {
              text: "DESKTOP AMBIENCE"
              color: Color.accent
              font.family: Style.font.family
              font.pixelSize: Style.font.caption
              font.bold: true
              font.letterSpacing: 1.8
            }

            Text {
              text: "Compose the atmosphere"
              color: Color.foreground
              font.family: Style.font.family
              font.pixelSize: Style.font.heading
              font.bold: true
            }
          }

          Row {
            anchors.right: closeButton.left
            anchors.rightMargin: Style.space(12)
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.space(8)

            Rectangle {
              anchors.verticalCenter: parent.verticalCenter
              width: Style.space(7)
              height: width
              radius: width / 2
              color: root.persistenceColor()
              opacity: root.settings && root.settings.persistenceState === "saved" ? 0.65 : 1
            }

            Text {
              anchors.verticalCenter: parent.verticalCenter
              text: root.persistenceName()
              color: root.muted
              font.family: Style.font.family
              font.pixelSize: Style.font.bodySmall
            }

            Button {
              visible: root.settings && root.settings.retryAvailable
              text: "Retry"
              bordered: true
              focusable: true
              onClicked: root.retryPersistence()
            }
          }

          Button {
            id: closeButton
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: "Close"
            bordered: true
            focusable: true
            onClicked: root.requestClose()
          }
        }

        Rectangle { width: parent.width; height: 1; color: root.faint }

        Row {
          width: parent.width
          height: Math.max(0, windowLayout.height - y)
          spacing: Style.space(14)

          BorderSurface {
            id: compositionPanel
            width: Math.max(260, Math.min(310, parent.width * 0.34))
            height: parent.height
            radius: Style.cornerRadius
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.035)
            borderSpec: Border.controlSpec("normal", Color.foreground, Color.accent)

            Flickable {
              anchors.top: parent.top
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.bottom: iconFooter.top
              anchors.margins: Style.space(14)
              anchors.bottomMargin: Style.space(10)
              contentWidth: width
              contentHeight: compositionColumn.implicitHeight
              clip: true
              boundsBehavior: Flickable.StopAtBounds
              QQC.ScrollBar.vertical: QQC.ScrollBar {}

              Column {
                id: compositionColumn
                width: parent.width - Style.space(6)
                spacing: Style.space(9)

                PanelSectionHeader { text: "GLOBAL" }

                ToggleSetting {
                  width: parent.width
                  label: "Ambience"
                  hint: checked ? "The selected stack is mapped." : "All ordered effects are hidden."
                  checked: root.settings ? root.settings.enabled : false
                  onToggledTo: function(value) { root.setEnabled(value) }
                }

                Text {
                  text: "PRESENTATION"
                  color: root.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  font.bold: true
                }

                Row {
                  width: parent.width
                  spacing: Style.space(6)

                  Button {
                    width: (parent.width - parent.spacing) / 2
                    text: "Background"
                    selected: root.settings && root.settings.presentation === "background"
                    bordered: true
                    focusable: true
                    onClicked: root.setPresentation("background")
                  }

                  Button {
                    width: (parent.width - parent.spacing) / 2
                    text: "Foreground"
                    selected: root.settings && root.settings.presentation === "foreground"
                    bordered: true
                    focusable: true
                    tooltipText: "Click-through overlay; may cover shell chrome"
                    onClicked: root.setPresentation("foreground")
                  }
                }

                SliderSetting {
                  width: parent.width
                  label: "Global Opacity"
                  hint: "Scales every ordered effect together."
                  value: root.settings ? root.settings.opacity : 1
                  minimum: 0
                  maximum: 1
                  step: 0.01
                  valueText: Math.round(value * 100) + "%"
                  onCommitted: function(value) { root.setOpacity(value) }
                }

                ToggleSetting {
                  width: parent.width
                  label: "Reduced Motion"
                  hint: "Uses the calmer source timing where supported."
                  checked: root.settings ? root.settings.reduceMotion : false
                  onToggledTo: function(value) { root.setReduceMotion(value) }
                }

                Rectangle { width: parent.width; height: 1; color: root.faint }
                PanelSectionHeader { text: "ACTIVE STACK · FRONT TO BACK" }

                Text {
                  visible: root.activeOrder.length === 0
                  width: parent.width
                  text: "No effects selected. Add one below to begin."
                  color: root.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.bodySmall
                  wrapMode: Text.WordWrap
                }

                Repeater {
                  model: root.activeOrder

                  EffectStackRow {
                    required property string modelData
                    required property int index
                    width: compositionColumn.width
                    label: root.effectLabel(modelData)
                    position: index
                    selected: root.selectedEffectId === modelData
                    canMoveUp: index > 0
                    canMoveDown: index < root.activeOrder.length - 1
                    onSelectedEffect: root.selectedEffectId = modelData
                    onMoveUp: root.moveEffect(modelData, -1)
                    onMoveDown: root.moveEffect(modelData, 1)
                    onRemove: root.removeEffect(modelData)
                  }
                }

                Rectangle { width: parent.width; height: 1; color: root.faint }
                PanelSectionHeader { text: "ADD EFFECT" }

                Repeater {
                  model: root.effectDefinitions

                  Button {
                    required property var modelData
                    visible: !root.effectIsActive(modelData.id)
                    width: compositionColumn.width
                    text: "+  " + modelData.label
                    leftAlign: true
                    bordered: true
                    focusable: true
                    onClicked: root.addEffect(modelData.id)
                  }
                }

              }
            }

            Column {
              id: iconFooter
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.bottom: parent.bottom
              anchors.margins: Style.space(14)
              spacing: Style.space(7)

              Rectangle { width: parent.width; height: 1; color: root.faint }
              PanelSectionHeader { text: "BAR ICON · " + LauncherIcons.labelFor(root.barIconId).toUpperCase() }

              Grid {
                id: iconGrid
                width: parent.width
                columns: 4
                spacing: Style.space(6)

                Repeater {
                  model: root.launcherIcons

                  Button {
                    required property var modelData
                    width: (iconGrid.width - iconGrid.spacing * 3) / 4
                    text: modelData.glyph
                    tooltipText: modelData.label
                    selected: root.barIconId === modelData.id
                    bordered: true
                    focusable: true
                    onClicked: root.setBarIcon(modelData.id)
                  }
                }
              }
            }
          }

          BorderSurface {
            id: detailPanel
            width: parent.width - compositionPanel.width - parent.spacing
            height: parent.height
            radius: Style.cornerRadius
            color: Qt.rgba(Color.foreground.r, Color.foreground.g, Color.foreground.b, 0.025)
            borderSpec: Border.controlSpec("normal", Color.foreground, Color.accent)

            Flickable {
              anchors.fill: parent
              anchors.margins: Style.space(18)
              contentWidth: width
              contentHeight: detailColumn.implicitHeight
              clip: true
              boundsBehavior: Flickable.StopAtBounds
              QQC.ScrollBar.vertical: QQC.ScrollBar {}

              Column {
                id: detailColumn
                width: parent.width - Style.space(8)
                spacing: Style.space(10)

                Item {
                  width: parent.width
                  height: Style.space(64)

                  Rectangle {
                    width: Style.space(4)
                    height: parent.height
                    radius: width / 2
                    color: Color.accent
                  }

                  Column {
                    anchors.left: parent.left
                    anchors.leftMargin: Style.space(16)
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Style.space(3)

                    Text {
                      text: root.effectLabel(root.selectedEffectId)
                      color: Color.foreground
                      font.family: Style.font.family
                      font.pixelSize: Style.font.title
                      font.bold: true
                    }

                    Text {
                      text: root.effectIsActive(root.selectedEffectId)
                        ? "Active renderer · changes save immediately"
                        : "Not in the active stack"
                      color: root.muted
                      font.family: Style.font.family
                      font.pixelSize: Style.font.bodySmall
                    }
                  }

                  Button {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.effectIsActive(root.selectedEffectId) ? "Remove" : "Add to stack"
                    bordered: true
                    focusable: true
                    onClicked: root.effectIsActive(root.selectedEffectId)
                      ? root.removeEffect(root.selectedEffectId) : root.addEffect(root.selectedEffectId)
                  }
                }

                Repeater {
                  model: EffectRegistry.fieldDefinitions(root.selectedEffectId)

                  Loader {
                    required property var modelData
                    width: detailColumn.width
                    sourceComponent: modelData.type === "bool" ? boolFieldComponent
                      : modelData.type === "enum" ? enumFieldComponent : numericFieldComponent

                    Component {
                      id: boolFieldComponent
                      ToggleSetting {
                        width: parent.width
                        label: parent.modelData.label
                        hint: parent.modelData.hint
                        checked: root.effectValue(root.selectedEffectId, parent.modelData.key) === true
                        onToggledTo: function(value) {
                          root.setEffectField(root.selectedEffectId, parent.modelData.key, value)
                        }
                      }
                    }

                    Component {
                      id: numericFieldComponent
                      SliderSetting {
                        width: parent.width
                        label: parent.modelData.label
                        hint: parent.modelData.hint
                        value: Number(root.effectValue(root.selectedEffectId, parent.modelData.key))
                        minimum: Number(parent.modelData.minimum)
                        maximum: Number(parent.modelData.maximum)
                        step: Number(parent.modelData.step)
                        integer: parent.modelData.type === "int"
                        valueText: root.fieldValueText(parent.modelData, value)
                        onCommitted: function(value) {
                          root.setEffectField(root.selectedEffectId, parent.modelData.key, value)
                        }
                      }
                    }

                    Component {
                      id: enumFieldComponent
                      EnumSetting {
                        width: parent.width
                        label: parent.modelData.label
                        hint: parent.modelData.hint
                        options: parent.modelData.values
                        value: String(root.effectValue(root.selectedEffectId, parent.modelData.key) || "")
                        onCommitted: function(value) {
                          root.setEffectField(root.selectedEffectId, parent.modelData.key, value)
                        }
                      }
                    }
                  }
                }

                Rectangle { width: parent.width; height: 1; color: root.faint }

                Text {
                  text: "DEDICATED VIGNETTE"
                  color: Color.accent
                  font.family: Style.font.family
                  font.pixelSize: Style.font.caption
                  font.bold: true
                  font.letterSpacing: 1.4
                }

                Text {
                  width: parent.width
                  text: "Independent from the ordered stack and never reorderable."
                  color: root.muted
                  font.family: Style.font.family
                  font.pixelSize: Style.font.bodySmall
                  wrapMode: Text.WordWrap
                }

                ToggleSetting {
                  width: parent.width
                  label: "Background Vignette"
                  hint: "Darkens the outer edges of the full output."
                  checked: root.vignetteValue("enabled") === true
                  onToggledTo: function(value) { root.setVignetteField("enabled", value) }
                }

                SliderSetting {
                  width: parent.width
                  label: "Vignette Intensity"
                  hint: "Controls the dedicated edge treatment."
                  value: Number(root.vignetteValue("intensity"))
                  minimum: 0
                  maximum: 1
                  step: 0.01
                  valueText: Math.round(value * 100) + "%"
                  onCommitted: function(value) { root.setVignetteField("intensity", value) }
                }

                ToggleSetting {
                  width: parent.width
                  label: "Place Behind Animations"
                  hint: "Moves the vignette below the ordered renderer stack."
                  checked: root.vignetteValue("ignoreBackgroundAnimationLayer") === true
                  onToggledTo: function(value) {
                    root.setVignetteField("ignoreBackgroundAnimationLayer", value)
                  }
                }

                Rectangle { width: parent.width; height: 1; color: root.faint }

                Row {
                  width: parent.width
                  spacing: Style.space(8)

                  Button {
                    text: root.resetArmed ? "Confirm reset" : "Reset all"
                    bordered: true
                    focusable: true
                    accent: root.resetArmed ? Color.urgent : Color.accent
                    onClicked: root.requestReset()
                  }

                  Text {
                    width: parent.width - x
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.settings && root.settings.persistenceError !== ""
                      ? root.settings.persistenceError
                      : "Reset restores ambience and launcher defaults."
                    color: root.settings && root.settings.persistenceError !== "" ? Color.urgent : root.muted
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                    wrapMode: Text.WordWrap
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  component ToggleSetting: BorderSurface {
    id: toggleRow
    property string label: ""
    property string hint: ""
    property bool checked: false
    signal toggledTo(bool value)

    implicitHeight: Style.space(62)
    radius: Style.cornerRadius
    color: checked ? root.accentWash : "transparent"
    borderSpec: Border.controlSpec(checked ? "selected" : "normal", Color.foreground, Color.accent)

    Column {
      anchors.left: parent.left
      anchors.right: toggle.left
      anchors.leftMargin: Style.space(12)
      anchors.rightMargin: Style.space(10)
      anchors.verticalCenter: parent.verticalCenter
      spacing: Style.space(2)

      Text {
        width: parent.width
        text: toggleRow.label
        color: Color.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        font.bold: true
        elide: Text.ElideRight
      }

      Text {
        width: parent.width
        text: toggleRow.hint
        color: root.muted
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        elide: Text.ElideRight
      }
    }

    ToggleSwitch {
      id: toggle
      anchors.right: parent.right
      anchors.rightMargin: Style.space(8)
      anchors.verticalCenter: parent.verticalCenter
      checked: toggleRow.checked
      onToggled: toggleRow.toggledTo(!toggleRow.checked)
    }
  }

  component SliderSetting: BorderSurface {
    id: sliderRow
    property string label: ""
    property string hint: ""
    property string valueText: ""
    property real value: 0
    property real minimum: 0
    property real maximum: 1
    property real step: 0.01
    property bool integer: false
    signal committed(real value)

    implicitHeight: Style.space(82)
    radius: Style.cornerRadius
    color: "transparent"
    borderSpec: Border.controlSpec("normal", Color.foreground, Color.accent)

    Text {
      anchors.left: parent.left
      anchors.top: parent.top
      anchors.leftMargin: Style.space(12)
      anchors.topMargin: Style.space(9)
      text: sliderRow.label
      color: Color.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      font.bold: true
    }

    Text {
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.rightMargin: Style.space(12)
      anchors.topMargin: Style.space(9)
      text: sliderRow.valueText
      color: Color.accent
      font.family: Style.font.family
      font.pixelSize: Style.font.bodySmall
      font.bold: true
    }

    Text {
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.leftMargin: Style.space(12)
      anchors.rightMargin: Style.space(12)
      anchors.topMargin: Style.space(29)
      text: sliderRow.hint
      color: root.muted
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      elide: Text.ElideRight
    }

    PanelSlider {
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.bottom: parent.bottom
      anchors.leftMargin: Style.space(12)
      anchors.rightMargin: Style.space(12)
      anchors.bottomMargin: Style.space(5)
      bar: root.controlPalette
      value: sliderRow.value
      minimum: sliderRow.minimum
      maximum: sliderRow.maximum
      step: sliderRow.step
      integer: sliderRow.integer
      onReleased: function(value) { sliderRow.committed(value) }
    }
  }

  component EnumSetting: BorderSurface {
    id: enumRow
    property string label: ""
    property string hint: ""
    property string value: ""
    property var options: []
    signal committed(string value)

    implicitHeight: Style.space(74)
    radius: Style.cornerRadius
    color: "transparent"
    borderSpec: Border.controlSpec("normal", Color.foreground, Color.accent)

    Column {
      anchors.left: parent.left
      anchors.right: selector.left
      anchors.leftMargin: Style.space(12)
      anchors.rightMargin: Style.space(12)
      anchors.verticalCenter: parent.verticalCenter
      spacing: Style.space(2)

      Text {
        width: parent.width
        text: enumRow.label
        color: Color.foreground
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        font.bold: true
        elide: Text.ElideRight
      }

      Text {
        width: parent.width
        text: enumRow.hint
        color: root.muted
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        elide: Text.ElideRight
      }
    }

    Dropdown {
      id: selector
      anchors.right: parent.right
      anchors.rightMargin: Style.space(10)
      anchors.verticalCenter: parent.verticalCenter
      width: Math.min(Style.space(210), enumRow.width * 0.42)
      showLabel: false
      value: enumRow.value
      options: enumRow.options
      onChanged: function(value) { enumRow.committed(value) }
    }
  }

  component EffectStackRow: BorderSurface {
    id: stackRow
    property string label: ""
    property int position: 0
    property bool selected: false
    property bool canMoveUp: false
    property bool canMoveDown: false
    signal selectedEffect()
    signal moveUp()
    signal moveDown()
    signal remove()

    implicitHeight: Style.space(50)
    radius: Style.cornerRadius
    color: selected ? root.accentWash : "transparent"
    borderSpec: Border.controlSpec(selected ? "selected" : "normal", Color.foreground, Color.accent)

    Button {
      anchors.left: parent.left
      anchors.right: actions.left
      anchors.top: parent.top
      anchors.bottom: parent.bottom
      text: String(stackRow.position + 1).padStart(2, "0") + "  " + stackRow.label
      leftAlign: true
      focusable: true
      selected: stackRow.selected
      onClicked: stackRow.selectedEffect()
    }

    Row {
      id: actions
      anchors.right: parent.right
      anchors.rightMargin: Style.space(4)
      anchors.verticalCenter: parent.verticalCenter
      spacing: 1

      Button {
        text: "↑"
        focusable: stackRow.canMoveUp
        visible: stackRow.canMoveUp
        tooltipText: "Move toward the front"
        onClicked: stackRow.moveUp()
      }
      Button {
        text: "↓"
        focusable: stackRow.canMoveDown
        visible: stackRow.canMoveDown
        tooltipText: "Move toward the back"
        onClicked: stackRow.moveDown()
      }
      Button {
        text: "×"
        focusable: true
        tooltipText: "Remove from stack"
        onClicked: stackRow.remove()
      }
    }
  }
}
