import tempfile
import unittest
from pathlib import Path

from qml_harness import HAVE_SESSION, parse_behave, qml_url, require_no_qml_errors, run_quickshell


@unittest.skipUnless(HAVE_SESSION, "needs a quickshell binary and a Wayland session")
class QmlPhase2InjectionBehaviorTests(unittest.TestCase):
    def test_setting_updates_and_reorder_preserve_identity_while_disable_unloads(self):
        qml = f'''
import Quickshell
import QtQuick

ShellRoot {{
  QtObject {{
    id: state
    property var activeEffects: ["crt", "filmGrain"]
    property real opacity: 0.5
    property bool reduceMotion: true
    property var effects: ({{
      crt: {{ enabled: true, intensity: 0.8, speed: 1, scanlineSpacing: 3,
        staticBandHeight: 150, staticAmount: 0.24, glowAmount: 0.22,
        bloomPulse: true, bloomPulseAmount: 0.52, bloomPulseInterval: 18000,
        distortion: true, distortionAmount: 0.45, vignette: true }},
      filmGrain: {{ enabled: true, intensity: 0.4, speed: 1,
        grainCount: 32, grainSize: 1.35, accentBlend: 0.18 }}
    }})
  }}

  Item {{
    id: host
    width: 32
    height: 32
    property var crtIdentity: null
    property var grainIdentity: null
    property var rebound: ({{}})

    Loader {{
      id: stackLoader
      anchors.fill: parent
      source: "{qml_url('components/AmbienceStack.qml')}"
      onLoaded: {{
        item.settings = state
        item.foregroundOverlay = true
        firstProbe.restart()
      }}
    }}

    Timer {{
      id: firstProbe
      interval: 100
      onTriggered: {{
        var stack = stackLoader.item
        var crt = stack.productionEffectObject("crt")
        var grain = stack.productionEffectObject("filmGrain")
        host.crtIdentity = crt
        host.grainIdentity = grain
        host.initial = {{
          count: stack.activeProductionEffectCount,
          crtIntensity: crt.effectiveIntensity,
          grainIntensity: grain.effectiveIntensity,
          reducedMotion: crt.reducedMotion,
          foregroundOverlay: crt.foregroundOverlay
        }}
        state.effects = {{
          crt: {{ enabled: true, intensity: 0.6, speed: 1, scanlineSpacing: 3,
            staticBandHeight: 150, staticAmount: 0.24, glowAmount: 0.22,
            bloomPulse: true, bloomPulseAmount: 0.52, bloomPulseInterval: 18000,
            distortion: true, distortionAmount: 0.45, vignette: true }},
          filmGrain: {{ enabled: true, intensity: 0.9, speed: 1,
            grainCount: 32, grainSize: 1.35, accentBlend: 0.18 }}
        }}
        state.activeEffects = ["filmGrain", "crt"]
        state.opacity = 0.25
        state.reduceMotion = false
        reboundProbe.restart()
      }}
    }}

    property var initial: ({{}})
    Timer {{
      id: reboundProbe
      interval: 80
      onTriggered: {{
        var stack = stackLoader.item
        var crt = stack.productionEffectObject("crt")
        var grain = stack.productionEffectObject("filmGrain")
        host.rebound = {{
          count: stack.activeProductionEffectCount,
          sameCrt: host.crtIdentity === crt,
          sameGrain: host.grainIdentity === grain,
          crtIntensity: crt.effectiveIntensity,
          reducedMotion: crt.reducedMotion,
          foregroundOverlay: crt.foregroundOverlay,
          grainZ: stack.zForEffect("filmGrain"),
          crtZ: stack.zForEffect("crt")
        }}
        var next = state.effects
        next.filmGrain.enabled = false
        state.effects = Object.assign({{}}, next)
        disabledProbe.restart()
      }}
    }}

    Timer {{
      id: disabledProbe
      interval: 80
      onTriggered: {{
        var stack = stackLoader.item
        console.log("BEHAVE " + JSON.stringify({{
          initial: host.initial,
          rebound: host.rebound,
          disabledCount: stack.activeProductionEffectCount,
          sameCrtAfterDisable: host.crtIdentity === stack.productionEffectObject("crt"),
          grainUnloaded: stack.productionEffectObject("filmGrain") === null
        }}))
        Qt.quit()
      }}
    }}
  }}
}}
'''
        with tempfile.TemporaryDirectory() as config_home:
            output = run_quickshell(qml, timeout=10, config_home=Path(config_home))
        require_no_qml_errors(output)
        row = parse_behave(output)[-1]
        self.assertEqual(row["initial"]["count"], 2, output[-2000:])
        self.assertAlmostEqual(row["initial"]["crtIntensity"], 0.4, places=5)
        self.assertAlmostEqual(row["initial"]["grainIntensity"], 0.2, places=5)
        self.assertTrue(row["initial"]["reducedMotion"])
        self.assertTrue(row["initial"]["foregroundOverlay"])
        self.assertEqual(row["rebound"]["count"], 2)
        self.assertTrue(row["rebound"]["sameCrt"])
        self.assertTrue(row["rebound"]["sameGrain"])
        self.assertAlmostEqual(row["rebound"]["crtIntensity"], 0.15, places=5)
        self.assertFalse(row["rebound"]["reducedMotion"])
        self.assertTrue(row["rebound"]["foregroundOverlay"])
        self.assertGreater(row["rebound"]["grainZ"], row["rebound"]["crtZ"])
        self.assertEqual(row["disabledCount"], 1)
        self.assertTrue(row["sameCrtAfterDisable"])
        self.assertTrue(row["grainUnloaded"])


if __name__ == "__main__":
    unittest.main()
