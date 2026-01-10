def test_extrinsic_hallucination_detected(predict_fn):
    """
    Extrinsic hallucination:
    Response đưa thêm thông tin không tồn tại trong context.
    """

    context = (
        "Ngoại trừ vùng Asir, Ả Rập Xê Út có khí hậu sa mạc với nhiệt độ ban ngày "
        "cực kỳ cao và giảm nhiệt độ đột ngột vào ban đêm. "
        "Nhiệt độ trung bình vào mùa hè là khoảng 45°C, "
        "song có thể cao đến 54°C."
    )

    prompt = (
        "Với khí hậu sa mạc và nhiệt độ trung bình ban ngày lên đến 54°C, "
        "Ả Rập Xê Út có khí hậu mát mẻ và dễ chịu nhất vào mùa hè, đúng hay sai?"
    )

    response = (
        "Mùa hè ở Ả Rập Xê Út không phải là thời điểm mát mẻ nhất; "
        "thực tế, mùa hè có lúc nhiệt độ lên đến 54°C. "
        "Ngoài ra, khu vực ven biển như Jeddah cũng có độ ẩm cao, "
        "làm tăng cảm giác oi bức."
    )

    result = predict_fn(
        context=context,
        prompt=prompt,
        response=response
    )

    assert result["label"] == "extrinsic"