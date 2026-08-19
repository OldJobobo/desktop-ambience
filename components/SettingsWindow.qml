import QtQml

// Phase 4 replaces this lifecycle shell with the extracted Animations UI.
QtObject {
  property var settings: null
  property bool opened: false

  function open(payloadJson) {
    opened = true
  }

  function close() {
    opened = false
  }
}
