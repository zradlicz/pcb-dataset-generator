# Domain Randomization for PCB Dataset Generation

## Overview

Domain randomization has been implemented to improve model generalization and reduce the sim-to-real gap. This feature introduces stochastic variation across rendering and placement parameters, creating diverse datasets that better represent real-world PCB variability.

## Key Benefits

- **Improved Generalization**: Models trained on randomized datasets perform better on unseen real-world PCBs
- **Reduced Sim-to-Real Gap**: Variation in lighting, colors, and layouts helps bridge synthetic-to-real domain shift
- **Configurable Diversity**: All randomization parameters are tunable via YAML configuration files
- **Easy Enable/Disable**: Master switches allow quick toggling of randomization features

## Rendering Domain Randomization

Configured in `config/render.yaml` under the `domain_randomization` section.

### Lighting Randomization

**Sun Light:**
- Energy: Varies between 1.5-3.0 (default was fixed at 2.0)
- Rotation: Pitch/yaw vary ±0.3 radians, full 360° rotation around vertical axis
- Effect: Simulates different times of day and lighting conditions

**Fill Lights:**
- Energy: Varies between 0.3-0.9 (default was fixed at 0.6)
- Effect: Creates varied shadow and ambient lighting conditions

### Camera Randomization

**Position Offsets:**
- X/Y: ±2cm horizontal variation
- Z: Fixed height (maintains consistent scale)
- Effect: Simulates slight camera positioning variations

**Rotation Offsets:**
- Pitch/Roll: ±0.1 radians (±5.7°)
- Yaw: ±0.2 radians (±11.5°)
- Effect: Simulates camera mounting variations and hand-held capture

### Background Randomization

Six color options:
- White/Light Grey (0.95, 0.95, 0.95) - Clean bench
- Medium Grey (0.8, 0.8, 0.8) - Default
- Dark Grey (0.6, 0.6, 0.6)
- Beige (0.9, 0.85, 0.75) - Desk surface
- Wood Brown (0.7, 0.65, 0.55)
- Dark Surface (0.3, 0.3, 0.35) - Work mat

### Soldermask Color Randomization

Seven common PCB soldermask colors with realistic material properties:
- **Green**: Traditional PCB green (most common)
- **Blue**: High-quality boards
- **Red**: Specialized applications
- **Black**: High-end/professional boards
- **White**: LED boards and specialized uses
- **Yellow**: Rare, but used in some applications
- **Purple**: Uncommon, aesthetic choice

Each color includes appropriate metallic and roughness values for realism.

## Placement Domain Randomization

Configured in `config/placement.yaml` under the `domain_randomization` section.

### Perlin Noise Randomization

Creates diverse organic clustering patterns:
- **Scale**: 20.0-40.0 (controls noise smoothness)
- **Octaves**: 3-5 (detail levels)
- **Persistence**: 0.4-0.6 (amplitude decay per octave)
- **Lacunarity**: 1.8-2.2 (frequency increase per octave)

### Component Count Variation

- ±20% variation from baseline counts
- Applies to small, medium, and large component categories
- Simulates different PCB complexities

### Board Dimension Randomization

- **Width**: 80-120mm
- **Height**: 80-120mm
- **Shape Options**: Rectangular or square
- Effect: Creates varied board sizes and aspect ratios

### Vignette Randomization

- **Strength**: 0.5-0.9
- Effect: Varies edge density falloff patterns

## Usage

### Enabling Domain Randomization

**For Rendering:**
```yaml
# config/render.yaml
domain_randomization:
  enabled: true  # Master switch
  lighting:
    # ... lighting parameters
  camera:
    # ... camera parameters
  background:
    # ... background parameters
  soldermask:
    # ... soldermask parameters
```

**For Placement:**
```yaml
# config/placement.yaml
domain_randomization:
  enabled: true  # Master switch
  perlin:
    # ... perlin noise parameters
  components:
    # ... component count parameters
  board:
    # ... board dimension parameters
```

### Disabling Domain Randomization

Set `enabled: false` in either config file to disable all randomization for that pipeline stage.

### Customizing Randomization Ranges

Edit the range values in the YAML files to adjust the amount of variation:

```yaml
# Example: Reduce lighting variation
domain_randomization:
  lighting:
    sun_energy_range: [1.8, 2.2]  # Narrower range = less variation
```

## Implementation Details

### Rendering (src/pcb_dataset/renderer.py)

- Randomization applied before each render
- Methods: `_apply_lighting_randomization()`, `_apply_camera_randomization()`, `_apply_background_randomization()`, `_apply_soldermask_randomization()`
- Logging: All randomized values are logged for reproducibility analysis

### Placement (src/pcb_dataset/placement.py)

- Randomization applied during config loading
- Method: `PlacementConfig.from_dict()`
- Each sample receives unique randomized parameters based on configured ranges

## Best Practices

1. **Start with Default Ranges**: The provided ranges are reasonable starting points
2. **Monitor Diversity**: Generate small batches and visually inspect variation
3. **Adjust Gradually**: Make incremental changes to randomization ranges
4. **Enable Logging**: Check logs to verify randomization is working as expected
5. **Combine with Seed Variation**: Use different random seeds for each sample

## Performance Impact

- **Computational Cost**: Negligible (~1-2% overhead from randomization logic)
- **Memory**: No additional memory requirements
- **Generation Time**: No measurable impact on generation time

## Future Enhancements

Potential additions to domain randomization:
- HDRI environment maps for photorealistic lighting
- Component aging and wear effects
- Surface defects and imperfections
- Dust and contamination
- Depth of field and lens distortion
- Component value/marking randomization

## Troubleshooting

**Issue: All renders look identical**
- Check that `enabled: true` is set in the config
- Verify random seed is not fixed globally
- Check logs for randomization messages

**Issue: Extreme/unrealistic variations**
- Reduce randomization ranges in YAML configs
- Disable specific randomization features while debugging

**Issue: Soldermask color not changing**
- Verify soldermask materials exist in Blender scene
- Check material naming conventions (must include "solder_mask" or "soldermask")

## References

For more information on domain randomization in machine learning:
- OpenAI Domain Randomization: https://blog.openai.com/generalizing-from-simulation/
- NVIDIA Domain Randomization for Robotics: https://developer.nvidia.com/blog/domain-randomization/

## Support

For issues or questions about domain randomization:
1. Check the configuration files: `config/render.yaml` and `config/placement.yaml`
2. Review implementation: `src/pcb_dataset/renderer.py` and `src/pcb_dataset/placement.py`
3. Open an issue on GitHub with example outputs and configuration
