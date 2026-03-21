from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta, datetime
import os, json

app = Flask(__name__)
app.secret_key = "silver_admin_secret"
app.permanent_session_lifetime = timedelta(days=1)

# 1. Firebase 초기화
if not firebase_admin._apps:
    try:
        # 파일 이름이 'firebase_key.json'인지 꼭 확인!
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"⚠️ 파이어베이스 키 파일 오류: {e}")

db = firestore.client()

ADMIN_PASSWORD = "4357"

# 2. 메인 페이지 (한국 시간 변환 로직 적용 ⭐)
@app.route("/")
def index():
    try:
        posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING)
        posts = []
        for doc in posts_ref.stream():
            post = doc.to_dict()
            post["id"] = doc.id
            
            # ⏰ 파이어베이스 시간(UTC)을 한국 시간(KST)으로 변환 (+9시간)
            if "created" in post and post["created"]:
                try:
                    # UTC 시간에 9시간을 더해줍니다.
                    kst_time = post["created"] + timedelta(hours=9)
                    post["time_display"] = kst_time.strftime('%m.%d %H:%M')
                except:
                    post["time_display"] = "시간 정보 없음"
            else:
                post["time_display"] = "방금 전"

            post["comments"] = []
            comments_ref = db.collection("posts").document(doc.id).collection("comments")
            for c in comments_ref.stream():
                c_data = c.to_dict()
                c_data["id"] = c.id
                post["comments"].append(c_data)
            posts.append(post)
        return render_template("index.html", posts=posts)
    except Exception as e:
        return f"연결 에러: {e}"

# 3. 글 및 댓글 작성
@app.route("/submit", methods=["POST"])
def submit():
    db.collection("posts").add({
        "nickname": request.form["nickname"],
        "content": request.form["content"],
        "reported": False,
        "created": firestore.SERVER_TIMESTAMP
    })
    return redirect("/")

@app.route("/comment/<post_id>", methods=["POST"])
def comment(post_id):
    db.collection("posts").document(post_id).collection("comments").add({
        "nickname": request.form["nickname"],
        "content": request.form["content"],
        "reported": False,
        "created": firestore.SERVER_TIMESTAMP
    })
    return redirect("/")

# 4. 신고 기능
@app.route("/report/post/<post_id>", methods=["POST"])
def report_post(post_id):
    db.collection("posts").document(post_id).update({
        "reported": True,
        "report_reason": request.form["reason"]
    })
    return redirect("/")

@app.route("/report/comment/<post_id>/<comment_id>", methods=["POST"])
def report_comment(post_id, comment_id):
    db.collection("posts").document(post_id).collection("comments").document(comment_id).update({
        "reported": True,
        "report_reason": request.form["reason"]
    })
    return redirect("/")

# 5. 관리자 기능 (관리자 페이지에서도 한국 시간 적용)
@app.route("/silver_admin_hidden_2464", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/silver_admin_hidden_2464")
        return "<script>alert('비번 틀림!'); history.back();</script>"
    
    if not session.get("admin"):
        return render_template("admin_login.html")
    
    posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING)
    posts = []
    for doc in posts_ref.stream():
        post = doc.to_dict()
        post["id"] = doc.id
        
        # 관리자 페이지에서도 시간 맞추기
        if "created" in post and post["created"]:
            kst_time = post["created"] + timedelta(hours=9)
            post["time_display"] = kst_time.strftime('%m.%d %H:%M')
        
        post["comments"] = []
        c_ref = db.collection("posts").document(doc.id).collection("comments")
        for c in c_ref.stream():
            c_data = c.to_dict()
            c_data["id"] = c.id
            post["comments"].append(c_data)
        posts.append(post)
    
    return render_template("admin.html", posts=posts)

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# 6. 관리자 삭제 기능
@app.route("/admin/delete/post/<post_id>", methods=["POST"])
def delete_post(post_id):
    if not session.get("admin"): return redirect("/")
    db.collection("posts").document(post_id).delete()
    return redirect("/silver_admin_hidden_2464")

@app.route("/admin/delete/comment/<post_id>/<comment_id>", methods=["POST"])
def delete_comment(post_id, comment_id):
    if not session.get("admin"): return redirect("/")
    db.collection("posts").document(post_id).collection("comments").document(comment_id).delete()
    return redirect("/silver_admin_hidden_2464")

if __name__ == "__main__":
    app.run(debug=True)