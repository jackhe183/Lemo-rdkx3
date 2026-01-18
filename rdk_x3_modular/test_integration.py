#!/usr/bin/env python3
# Integration Test Script for RDK X3 Modular Drivers

import sys
import time


def test_camera():
    """Test camera: open, capture one photo, exit cleanly"""
    print("\n[TEST 1/3] Camera Driver")
    print("-" * 30)

    try:
        from drivers import Camera

        # Test as context manager
        with Camera() as cam:
            print("✓ Camera opened successfully")

            frame = cam.get_frame_bgr()
            if frame is not None:
                print(f"✓ Frame captured: {frame.shape}")

                # Save test photo
                import cv2
                cv2.imwrite("test_photo.jpg", frame)
                print("✓ Photo saved: test_photo.jpg")
            else:
                print("✗ Failed to capture frame")
                return False

        # Context manager should auto-close
        print("✓ Camera closed automatically")
        return True

    except Exception as e:
        print(f"✗ Camera test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audio():
    """Test audio: record 1 second, exit cleanly"""
    print("\n[TEST 2/3] Audio Driver")
    print("-" * 30)

    try:
        from drivers import Audio

        audio = Audio()
        print("✓ Audio driver initialized")

        # Record 1 second
        print("Recording 1 second...")
        audio.record("test_record.wav", 1)
        print("✓ Recording saved: test_record.wav")

        return True

    except Exception as e:
        print(f"✗ Audio test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mediapipe():
    """Test MediaPipe: verify installation and performance"""
    print("\n[TEST 3/3] MediaPipe Hands")
    print("-" * 30)

    try:
        import mediapipe as mp
        print(f"✓ MediaPipe version: {mp.__version__}")

        # Create hands instance with model_complexity=0
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,  # Fastest model
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("✓ Hands model loaded (complexity=0)")

        # Test with a dummy frame
        import numpy as np
        dummy_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        import cv2
        frame_rgb = cv2.cvtColor(dummy_frame, cv2.COLOR_BGR2RGB)

        start = time.time()
        results = hands.process(frame_rgb)
        elapsed = (time.time() - start) * 1000

        print(f"✓ Process time: {elapsed:.1f}ms")

        if elapsed < 50:
            print("✓ Performance OK (< 50ms)")
        else:
            print(f"⚠ Warning: Processing exceeds 50ms target")

        hands.close()
        return True

    except Exception as e:
        print(f"✗ MediaPipe test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests"""
    import argparse

    parser = argparse.ArgumentParser(description='RDK X3 Integration Test')
    parser.add_argument('--skip-camera', action='store_true',
                       help='Skip camera test (if hardware unavailable)')
    args = parser.parse_args()

    print("=" * 50)
    print("RDK X3 Integration Test")
    print("=" * 50)

    results = {}

    if not args.skip_camera:
        results["Camera"] = test_camera()
    else:
        print("\n[SKIP] Camera test (skipped by user)")
        results["Camera"] = None
        
    if results.get("Camera") is False:
        print("\nCamera failed.")
        return 1

    results["Audio"] = test_audio()
    results["MediaPipe"] = test_mediapipe()

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    for name, passed in results.items():
        if passed is None:
            status = "SKIPPED"
            symbol = "−"
        elif passed:
            status = "PASSED"
            symbol = "✓"
        else:
            status = "FAILED"
            symbol = "✗"
        print(f"{symbol} {name}: {status}")

    executed = [v for v in results.values() if v is not None]
    all_passed = all(executed) if executed else False

    print("\n" + ("=" * 50))
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("=" * 50)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
