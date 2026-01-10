def test_no_hallucination_detected(predict_fn):
    """
    No hallucination:
    Response hoàn toàn đúng và không thêm thông tin ngoài context.
    """

    context = (
        "Hồ Gươm là một hồ nước ngọt nằm ở trung tâm thủ đô Hà Nội, Việt Nam. "
        "Hồ còn có tên gọi khác là hồ Hoàn Kiếm."
    )

    prompt = "Hồ Gươm nằm ở đâu?"

    response = "Hồ Gươm nằm ở trung tâm thủ đô Hà Nội."

    result = predict_fn(
        context=context,
        prompt=prompt,
        response=response
    )

    assert result["label"] == "no"