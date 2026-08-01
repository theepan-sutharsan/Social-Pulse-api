"""
Social Pulse API — Multi-Platform Analytics Controller
Handles multi-platform growth, predictions, competitor comparisons, post analytics, and AI scores across YouTube, Instagram, Facebook, TikTok, X, and LinkedIn.
"""
from flask import jsonify, request
from flask_jwt_extended import get_current_user
from app.models.connected_account_model import ConnectedAccount
from app.models.tracked_channel_model import TrackedChannel
from app.models.account_history_model import AccountHistory
from app.models.post_history_model import PostHistory
from app.models.video_model import Video
from app.services import growth_engine, prediction_engine, competitor_engine, revenue_engine, ai_scoring_engine, seo_engine


def get_account_growth(account_id: int):
    account = ConnectedAccount.query.get(account_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    acc_dict = account.to_dict()
    history = AccountHistory.get_history_for_account(account.platform_account_id, account.platform)
    growth = growth_engine.calculate_growth_metrics(history, acc_dict)

    return jsonify({
        "account": acc_dict,
        "growth": growth,
    }), 200


def get_account_predictions(account_id: int):
    account = ConnectedAccount.query.get(account_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    acc_dict = account.to_dict()
    history = AccountHistory.get_history_for_account(account.platform_account_id, account.platform)

    sub_pred = prediction_engine.predict_subscriber_growth(history, acc_dict.get("subscribers", 0))
    view_pred = prediction_engine.predict_view_growth(history, acc_dict.get("total_views", 0))

    return jsonify({
        "account": acc_dict,
        "follower_predictions": sub_pred,
        "view_predictions": view_pred,
    }), 200


def get_account_competitors(account_id: int):
    account = ConnectedAccount.query.get(account_id)
    if not account:
        return jsonify({"error": "Account not found."}), 404

    # Find candidate tracked competitor channels
    competitors = TrackedChannel.query.filter_by(platform=account.platform).limit(5).all()
    user_posts = [v.to_dict() for v in account.videos]

    comps_result = []
    for comp in competitors:
        comp_posts = [v.to_dict() for v in comp.videos]
        comp_res = competitor_engine.compare_user_vs_competitor(account.to_dict(), user_posts, comp.to_dict(), comp_posts)
        comps_result.append(comp_res)

    return jsonify({
        "account": account.to_dict(),
        "competitors_count": len(comps_result),
        "competitor_comparisons": comps_result,
    }), 200


def compare_competitors():
    """
    POST endpoint: Compare user account or channel vs specific competitor.
    JSON: { "user_account_id": 1, "competitor_channel_id": "UC..." }
    """
    data = request.get_json(silent=True) or {}
    user_acc_id = data.get("user_account_id")
    comp_chan_id = data.get("competitor_channel_id")

    user_acc = ConnectedAccount.query.get(user_acc_id) if user_acc_id else None
    user_dict = user_acc.to_dict() if user_acc else {"display_name": "My Channel", "subscribers": 5000, "platform": "youtube"}
    user_posts = [v.to_dict() for v in (user_acc.videos if user_acc else [])]

    comp_chan = TrackedChannel.get_by_channel_id(str(comp_chan_id)) if comp_chan_id else None
    comp_dict = comp_chan.to_dict() if comp_chan else {"channel_name": "Competitor Channel", "subscribers": 12000, "platform": "youtube"}
    comp_posts = [v.to_dict() for v in (comp_chan.videos if comp_chan else [])]

    result = competitor_engine.compare_user_vs_competitor(user_dict, user_posts, comp_dict, comp_posts)
    return jsonify(result), 200


def get_post_analytics(post_id: int):
    post = Video.query.get(post_id)
    if not post:
        return jsonify({"error": "Post/Video not found."}), 404

    p_dict = post.to_dict()
    scores = ai_scoring_engine.calculate_ai_scores({"platform": post.platform}, [p_dict])

    return jsonify({
        "post": p_dict,
        "analytics": {
            "views": p_dict.get("views", 0),
            "likes": p_dict.get("likes", 0),
            "comments": p_dict.get("comments", 0),
            "shares": p_dict.get("shares", 0),
            "engagement_rate": p_dict.get("engagement_rate", 0.0),
            "quality_score": scores["scores"]["content_quality_score"],
        }
    }), 200


def get_post_seo(post_id: int):
    post = Video.query.get(post_id)
    if not post:
        return jsonify({"error": "Post/Video not found."}), 404

    seo_res = seo_engine.analyze_video_seo(post.to_dict())
    return jsonify({
        "post_id": post.id,
        "seo": seo_res,
    }), 200


def get_post_prediction(post_id: int):
    post = Video.query.get(post_id)
    if not post:
        return jsonify({"error": "Post/Video not found."}), 404

    p_dict = post.to_dict()
    history = PostHistory.get_history_for_post(post.external_id)
    pred = prediction_engine.predict_view_growth(history, p_dict.get("views", 0))

    return jsonify({
        "post_id": post.id,
        "prediction": pred,
    }), 200
