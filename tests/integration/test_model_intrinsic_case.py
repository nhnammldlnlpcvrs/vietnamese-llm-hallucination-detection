# tests/integration/test_model_intrinsic_case.py
def test_intrinsic_hallucination_detected(predict_fn):
    """
    Intrinsic hallucination:
    Response mâu thuẫn trực tiếp với context.
    """

    context = (
        "Sau khi tộc Chu lật đổ vương triều Thương, lập ra vương triều Chu, "
        "Chu Vũ Vương theo kiến nghị của Chu công Đán đã cho con của Trụ Vương "
        "là Vũ Canh tiếp tục cai trị đất Ân. "
        "Lãnh thổ của Ân gần tương ứng với khu vực bắc bộ tỉnh Hà Nam, "
        "nam bộ tỉnh Hà Bắc và đông nam bộ tỉnh Sơn Tây ngày nay."
    )

    prompt = "Khu vực nào ngày nay trước kia thuộc nước Ân?"

    response = (
        "Khu vực trước kia thuộc nước Ân ngày nay thuộc về phía tây nam tỉnh "
        "Tứ Xuyên, đông bắc tỉnh Quảng Tây và miền trung tỉnh Quảng Đông."
    )

    result = predict_fn(
        context=context,
        prompt=prompt,
        response=response
    )

    assert result["label"] == "intrinsic"
