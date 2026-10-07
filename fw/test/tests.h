#ifndef FW_TEST_TESTS_H
#define FW_TEST_TESTS_H
/* name, requirement: the list fw/test/test_main.c runs (fwsim maps results to FWSIM-R ids) */
#define FW_TESTS(T) \
    T(test_abi_hop_lengths, "FWSIM-R9") T(test_pwm_per_plan, "FWSIM-R25") T(test_abi_pure, "FWSIM-R3") T(test_abi_power_on_hold, "FWSIM-R3") \
    T(test_clamp_property, "FWSIM-R64") T(test_clamp_hard_limits, "FWSIM-R64") T(test_clamp_level_matches_amp, "FWSIM-R64") T(test_clamp_db_table, "FWSIM-R6") \
    T(test_knobs_table, "FWSIM-R6") T(test_knobs_enum_and_clamps, "FWSIM-R6") \
    T(test_store_roundtrip, "FWSIM-R6") T(test_store_power_fail_every_step, "FWSIM-R6") T(test_store_corruption, "FWSIM-R6") \
    T(test_store_version_and_clamp, "FWSIM-R6") T(test_store_faults, "FWSIM-R6") \
    T(test_replay_state_hash, "FWSIM-R3") \
    T(test_fakes_coverage, "FWSIM-R2") T(test_fakes_fault_injection, "FWSIM-R2") T(test_fakes_state, "FWSIM-R2") \
    T(test_fakes_adf_isr_ring, "FWSIM-R3") \
    T(test_app_loop, "FWSIM-R2") T(test_board_config, "FWSIM-R5") \
    T(test_dsp_math, "FWSIM-R4") T(test_dsp_silence_exact_centre, "FWSIM-R14") T(test_dsp_whines_only_squelched, "FWSIM-R14") \
    T(test_dsp_tone_passes_full_mode, "FWSIM-R13") T(test_dsp_variants, "FWSIM-R13") T(test_dsp_ceiling_short, "FWSIM-R15") \
    T(test_fsm_random_walk, "FWSIM-R18") T(test_gestures_b, "FWSIM-R29") T(test_rematch_two_presses, "FWSIM-R18") \
    T(test_docked_interlock, "FWSIM-R19") T(test_cdc_paths_clamp, "FWSIM-R64") T(test_cdc_frame_stream, "FWSIM-R28") T(test_usb_cdc_lifecycle_clamp, "FWSIM-R28") T(test_charger_plan, "FWSIM-R20") \
    T(test_charger_watchdog_faults, "FWSIM-R20") T(test_break_always_on, "FWSIM-R65") \
    T(test_stop2_sequence, "FWSIM-R23") T(test_led_duty, "FWSIM-R29") T(test_volume_ticks, "FWSIM-R29") T(test_idle_detector, "FWSIM-R18")
#define FW_TEST_DECL(fn, req) void fn(void);
FW_TESTS(FW_TEST_DECL)
#undef FW_TEST_DECL
#endif
