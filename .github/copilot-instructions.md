# Copilot Instructions - Automated Gel Nail Machine

## Project Overview
This is an R&D prototype for an automated gel nail application and UV curing system. The system uses computer vision (OpenCV + MediaPipe) for hand tracking and Raspberry Pi GPIO for safe UV LED control. **Safety is paramount** - this involves UV light and chemicals.

## Architecture: Modular Service Layer

```
Camera (USB) → HandTracker → (Future: MainController) ← UVLEDController → GPIO/PWM → UV LEDs
                    ↓                                          ↓
              Fingertip coords                           Safety timers
```

The codebase is intentionally modular with two independent components currently implemented:
- **`software/hand_tracking/`**: MediaPipe-based computer vision (standalone, ~30 FPS on Pi 4)
- **`software/uv_control/`**: PWM-controlled UV LED system with safety features (standalone)
- **Integration layer is NOT yet implemented** - modules run independently

## Critical Patterns & Conventions

### 1. Simulation Mode is Default
All hardware modules **must** support `simulation_mode=True` for dev/testing without Raspberry Pi:
```python
controller = UVLEDController(gpio_pin=18, simulation_mode=True)  # No hardware required
```
Use `simulation_mode=False` only on actual Pi hardware. Check `RPi.GPIO` availability with try/except.

### 2. Safety-First Error Handling
UV control has strict safety enforcement:
- Max continuous runtime: 5 minutes (`max_continuous_time=300`)
- Mandatory cooldown after 2+ minutes operation (`COOLDOWN_THRESHOLD_SECONDS=120`)
- Emergency stop **immediately** sets intensity to 0
- All UV operations should fail safely (turn off on exception)

Example pattern from `led_controller.py`:
```python
try:
    controller.cure_with_profile('gel_polish')
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    controller.emergency_stop()  # Always emergency stop on error
    raise
```

### 3. Curing Profiles Strategy Pattern
Add new profiles to `CURING_PROFILES` dict in `UVLEDController` class (lines 30-40):
```python
'new_product': CuringProfile('Product Name', duration_seconds=45, intensity_percent=85, pulse_mode=False)
```
Never hardcode timing - use profiles for consistency and safety validation.

### 4. MediaPipe Coordinate Translation
Hand landmarks are normalized (0.0-1.0). Always convert to pixel coords using frame shape:
```python
x = int(landmark.x * width)
y = int(landmark.y * height)
```
See `get_fingertip_positions()` in `hand_tracker.py` for reference implementation.

### 5. GPIO Pin Numbering
Use **BCM numbering** (not BOARD):
- GPIO 18 (Pin 12): LED PWM control
- GPIO 23 (Pin 16): Emergency stop
- GPIO 24/25 (Pins 18/22): Door interlocks
- GPIO 4 (Pin 7): Temperature sensor

## Development Workflows

### Testing Hand Tracking
```bash
python software/hand_tracking/hand_tracker.py  # Runs live demo with webcam
```
Press 'q' to quit. Shows fingertip positions and nail zones overlaid on video.

### Testing UV Control (Simulation)
```bash
python software/uv_control/led_controller.py  # Interactive menu, no hardware needed
```
Tests curing profiles, intensity control, cooldown logic.

### Dependencies
```bash
pip install -r requirements.txt  # Installs OpenCV, MediaPipe, NumPy
```
`RPi.GPIO` only installs on ARM platforms (auto-detected via platform_machine check).

### No Testing Framework Yet
Unit tests are planned but **not yet implemented**. Manual testing via `if __name__ == "__main__"` blocks is current practice.

## Key Files & Their Purposes

- **`software/hand_tracking/hand_tracker.py`**: Complete hand tracking implementation. Detect hands, extract 21 landmarks per hand, calculate fingertip positions and nail zones.
- **`software/uv_control/led_controller.py`**: UV LED control with PWM, safety timers, curing profiles. Supports both hardware and simulation.
- **`docs/SOFTWARE_ARCHITECTURE.md`**: Comprehensive design doc with class diagrams, data flows, future integration plans.
- **`docs/SAFETY.md`**: **Read before any UV-related changes.** UV exposure limits, chemical safety, electrical safety.
- **`docs/HARDWARE_SETUP.md`**: Complete BOM, wiring diagrams, GPIO pinout, assembly instructions.

## Common Tasks

### Adding a New Curing Profile
1. Add to `CURING_PROFILES` dict in `led_controller.py`
2. Use existing `CuringProfile` dataclass structure
3. Validate duration < `max_continuous_time` (300s)
4. Test with `cure_with_profile('profile_name')`

### Modifying Hand Detection Confidence
Adjust in `HandTracker.__init__()`:
```python
detection_confidence=0.7,  # Lower = more sensitive but false positives
tracking_confidence=0.5    # Lower = smoother but less accurate
```

### Adding Safety Checks
All safety logic goes in UV control module. Pattern:
1. Check safety condition (cooldown, interlock, temp)
2. If unsafe: log error, call `emergency_stop()`, return False
3. If safe: proceed with operation

### Future Integration Work
When building `integration/main_controller.py`:
- Import both `HandTracker` and `UVLEDController`
- Coordinate tracking → positioning → curing workflow
- State machine pattern recommended (see `docs/SOFTWARE_ARCHITECTURE.md` - ApplicationStateMachine)
- Monitor safety conditions continuously during operation

## What NOT To Do

❌ **Never bypass safety features** (cooldown, emergency stop, max runtime)  
❌ **Don't remove simulation mode** - required for development workflow  
❌ **Don't hardcode timing values** - use `CuringProfile` pattern  
❌ **Don't assume hardware availability** - always check/handle `ImportError` for `RPi.GPIO`  
❌ **Don't modify MediaPipe hand landmark indices** - these are standardized (0-20)  
❌ **Don't commit without testing on webcam** (for CV) or in simulation mode (for UV)

## Project Status
**Phase**: Early prototype development  
**Complete**: Hand tracking, UV control modules (independent)  
**In Progress**: Documentation, safety validation  
**Not Started**: Integration layer, web UI, automated application, safety sensors implementation

## Questions or Unclear Patterns?
- Check `docs/SOFTWARE_ARCHITECTURE.md` for detailed class designs and data flows
- Review actual implementations in `software/` - code is primary documentation
- Safety concerns: Always reference `docs/SAFETY.md`
- Hardware questions: See `docs/HARDWARE_SETUP.md` for wiring and BOM
