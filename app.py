from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta, datetime
import os, json
import gc  # 1. 메모리 청소를 위해 추가

app = Flask(__name__)
app.secret_key = "silver_admin_secret"
app.permanent_session_lifetime = timedelta(days=1)

# Firebase 초기화
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"⚠️ 파이어베이스 키 파일 오류: {e}")

db = firestore.client()
ADMIN_PASSWORD = "4357"

# 메인 페이지 (메모리 최적화 적용 ⭐)
@app.route("/")
def index():
    try:
        # 최신글 20개만 가져오도록 제한 (메모리 보호)
        posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(20)
        posts = []
        
        # stream() 대신 get()을 사용하여 메모리 점유율을 낮춤
        docs = posts_ref.get()
        
        for doc in docs:
            post = doc.to_dict()
            post["id"] = doc.id
            
            if "created" in post and post["created"]:
                try:
                    kst_time = post["created"] + timedelta(hours=9)
                    post["time_display"] = kst_time.strftime('%m.%d %H:%M')
                except:
                    post["time_display"] = "시간 정보 없음"
            else:
                post["time_display"] = "방금 전"

            post["comments"] = []
            # 댓글도 최신순으로 가져오기
            comments_docs = db.collection("posts").document(doc.id).collection("comments").get()
            for c in comments_docs:
                c_data = c.to_dict()
                c_data["id"] = c.id
                post["comments"].append(c_data)
            posts.append(post)
        
        response = render_template("index.html", posts=posts)
        
        # 2. 페이지를 보여준 후 메모리 즉시 청소
        del posts
        gc.collect() 
        
        return response
    except Exception as e:
        return f"연결 에러: {e}"

# 글 작성
@app.route("/submit", methods=["POST"])
def submit():
    db.collection("posts").add({
        "nickname": request.form["nickname"],
        "content": request.form["content"],
        "reported": False,
        "created": firestore.SERVER_TIMESTAMP
    })
    gc.collect()
    return redirect("/")

# 댓글 작성
@app.route("/comment/<post_id>", methods=["POST"])
def comment(post_id):
    db.collection("posts").document(post_id).collection("comments").add({
        "nickname": request.form["nickname"],
        "content": request.form["content"],
        "reported": False,
        "created": firestore.SERVER_TIMESTAMP
    })
    gc.collect()
    return redirect("/")

# 신고 기능
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

# 관리자 페이지 (메모리 최적화 적용)
@app.route("/silver_admin_hidden_2464", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/silver_admin_hidden_2464")
        return "<script>alert('비번 틀림!'); history.back();</script>"
    
    if not session.get("admin"):
        return render_template("admin_login.html")
    
    posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(50)
    posts = []
    docs = posts_ref.get()
    
    for doc in docs:
        post = doc.to_dict()
        post["id"] = doc.id
        if "created" in post and post["created"]:
            kst_time = post["created"] + timedelta(hours=9)
            post["time_display"] = kst_time.strftime('%m.%d %H:%M')
        
        post["comments"] = []
        c_docs = db.collection("posts").document(doc.id).collection("comments").get()
        for c in c_docs:
            c_data = c.to_dict()
            c_data["id"] = c.id
            post["comments"].append(c_data)
        posts.append(post)
    
    res = render_template("admin.html", posts=posts)
    del posts
    gc.collect()
    return res

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# 관리자 삭제 기능
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
    # Render 환경에서는 환경변수 PORT를 사용해야 해
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
