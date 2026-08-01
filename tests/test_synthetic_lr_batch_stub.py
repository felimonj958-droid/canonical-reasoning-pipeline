from src.normalize.run_synthetic_lr_batch import run_synthetic_lr_batch


def test_run_synthetic_lr_batch_aggregates_results(monkeypatch):
    fake_outputs = [
        {
            "status": "valid",
            "destination": ("normalized", None),
            "content_quality": {
                "status": "pass",
                "flags": [],
            },
            "saved_path": "data/normalized/records/item1.json",
        },
        {
            "status": "needs_review",
            "destination": ("review", "synthetic_low_quality"),
            "content_quality": {
                "status": "review",
                "flags": ["meta_language_detected", "weak_argument_signals"],
            },
            "saved_path": "data/review_queue/synthetic_low_quality/item2.json",
        },
        {
            "status": "needs_review",
            "destination": ("review", "synthetic_low_quality"),
            "content_quality": {
                "status": "review",
                "flags": ["meta_language_detected"],
            },
            "saved_path": "data/review_queue/synthetic_low_quality/item3.json",
        },
        {
            "status": "valid",
            "destination": ("normalized", None),
            "content_quality": {
                "status": "pass",
                "flags": [],
            },
            "saved_path": "data/normalized/records/item4.json",
        },
    ]

    state = {"i": 0}

    def fake_run_synthetic_lr_lane(**kwargs):
        result = fake_outputs[state["i"] % len(fake_outputs)]
        state["i"] += 1
        return result

    monkeypatch.setattr(
        "src.normalize.run_synthetic_lr_batch.run_synthetic_lr_lane",
        fake_run_synthetic_lr_lane,
    )

    result = run_synthetic_lr_batch(
        model="gpt-4o-mini",
        n_per_config=1,
        persist=False,
    )

    summary = result["summary"]

    assert summary["total_items"] == 4
    assert summary["status_counts"]["valid"] == 2
    assert summary["status_counts"]["needs_review"] == 2
    assert summary["quality_status_counts"]["pass"] == 2
    assert summary["quality_status_counts"]["review"] == 2
    assert summary["quality_flag_counts"]["meta_language_detected"] == 2
    assert summary["quality_flag_counts"]["weak_argument_signals"] == 1
    assert summary["destination_counts"]["('normalized', None)"] == 2
    assert summary["destination_counts"]["('review', 'synthetic_low_quality')"] == 2
    assert len(result["results"]) == 4
