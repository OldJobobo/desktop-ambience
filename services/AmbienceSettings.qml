import QtQml

// Phase 2 adds normalization, atomic persistence, and recovery behavior here.
QtObject {
  readonly property int schemaVersion: 1
  readonly property bool persistenceReady: false
  readonly property string persistenceState: "scaffold"
}
