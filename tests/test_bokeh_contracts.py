from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_bokeh_registry_and_stack_contracts_are_opt_in_and_ordered_tenth():
    registry = read("services/EffectRegistry.js")
    stack = read("components/AmbienceStack.qml")

    assert registry.index('id: "trackingLines", label: "VHS"') < registry.index('id: "bokeh", label: "Bokeh"')
    for setting in (
        'intensity: realField(0.52, 0, 1)',
        'speed: realField(0.65, 0.15, 4)',
        'lightCount: intField(28, 6, 72)',
        'lightSize: realField(88, 20, 240)',
        'blurSoftness: realField(0.82, 0, 1)',
        'driftAmount: realField(0.42, 0, 1)',
        'twinkleAmount: realField(0.18, 0, 1)',
        'primaryColorRole: enumField("accent"',
        'secondaryColorRole: enumField("color13"',
    ):
        assert setting in registry
    for role in ("accent", "foreground", "color09", "color10", "color11", "color12", "color13", "color14"):
        assert f'"{role}"' in registry

    assert '"bokeh"' in stack
    assert "id: bokehComponent" in stack
    assert "id: bokehLoader" in stack
    assert 'active: root.productionEffectActive("bokeh")' in stack
    assert 'effectSettings: root.settingsFor("bokeh")' in stack
    assert "theme: root.theme" in stack
    assert "bokeh: bokehLoader" in stack


def test_bokeh_uses_three_grouped_blurs_and_bounded_deterministic_delegates():
    effect = read("effects/BokehEffect.qml")

    assert effect.count("MultiEffect {") == 3
    assert effect.count("layer.effect: MultiEffect {") == 3
    assert effect.count("Repeater {") == 3
    assert "readonly property int boundedDelegateCount" in effect
    assert "readonly property int activeBlurLayerCount" in effect
    assert "readonly property bool animationRunning" in effect
    assert "readonly property int overscan" in effect
    assert "function seededNoise(seed)" in effect
    assert "function phaseProgress(phase, reverse)" in effect
    assert "function delegateObject(lightIndex)" in effect
    assert "function lightSnapshot(lightIndex)" in effect
    assert "initialXPhase: root.seededNoise" in effect
    assert "initialYPhase: root.seededNoise" in effect
    assert "initialTwinklePhase: root.seededNoise" in effect
    assert "NumberAnimation on motionXPhase" in effect
    assert "NumberAnimation on motionYPhase" in effect
    assert "NumberAnimation on twinklePhase" in effect
    assert "to: light.initialXPhase + 2" in effect
    assert "to: light.initialYPhase + 2" in effect
    assert "to: light.initialTwinklePhase + 2" in effect
    assert "SequentialAnimation on motionX" not in effect
    assert "SequentialAnimation on motionY" not in effect
    assert "SequentialAnimation on breathingOpacity" not in effect
    assert "model: root.bandCount(0)" in effect
    assert "model: root.bandCount(1)" in effect
    assert "model: root.bandCount(2)" in effect
    assert "FrameAnimation" not in effect
    assert "Canvas" not in effect
    assert "Process {" not in effect
    assert "FileView" not in effect
    assert "ShaderEffect" not in effect
    assert "Particle" not in effect


def test_bokeh_is_registered_in_visual_performance_and_load_harnesses():
    visual = read("tests/live_phase6_visual.py")
    performance = read("tests/live_phase7_performance.py")
    fullscreen = read("tests/live_phase6_fullscreen.py")
    smoke = read("tests/test_qml_load_smoke.py")

    for case_id in (
        "bokeh", "bokehMinimum", "bokehMaximum", "bokehSharp", "bokehSoft",
        "bokehNoDrift", "bokehTwinkleOff", "bokehContrastingRoles", "bokehReducedMotion",
    ):
        assert f'("{case_id}", "effects/BokehEffect.qml")' in visual
    for case_id in (
        "bokeh", "bokehReducedMotion", "bokehMaximumPopulation",
        "bokehMaximumSoftness", "bokehHidden", "bokehFullscreenSuppressed",
    ):
        assert f'("{case_id}", "effects/BokehEffect.qml")' in performance
    assert "bokehMetrics" in performance
    assert "delegateCount" in performance
    assert "blurLayerCount" in performance
    assert "configure_temporary_output" in performance
    assert '"negativeOriginCovered"' in performance
    assert '"outputGeometry"' in performance
    assert "bokehThemeSwitch.png" in visual
    assert '"bokehThemeSwitchChangedPixels"' in visual
    assert '"activeEffects": ["bokeh"]' in fullscreen
    assert 'next.presentation = "background"' in fullscreen
    assert '"presentationModes": ["foreground", "background"]' in fullscreen
    assert '"bokehIdentityPreservedAcrossPresentation": True' in fullscreen
    assert '"bokeh"' in smoke
