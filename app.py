from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta, datetime
import os, json
import gc  # 메모리 관리를 위한 가비지 컬렉터

app = Flask(__name__)
app.secret_key = "silver_admin_secret"
app.permanent_session_lifetime = timedelta(days=1)

# 1. Firebase 초기화 (한 번만 실행되도록 설정)
if not firebase_admin._apps:
    try:
        # 파일 이름이 'firebase_key.json'인지 확인!
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"⚠️ 파이어베이스 키 파일 오류: {e}")

db = firestore.client()
ADMIN_PASSWORD = "4357"

# 2. 메인 페이지 (메모리 절약형 로직 ⭐)
@app.route("/")
def index():
    try:
        # 최신글 15개로 제한해서 메모리 폭발 방지
        posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(15)
        posts = []
        docs = posts_ref.get() # stream() 대신 get() 사용이 더 안전함
        
        for doc in docs:
            post = doc.to_dict()
            post["id"] = doc.id
            
            # 시간 변환 (+9시간)
            if "created" in post and post["created"]:
                try:
                    kst_time = post["created"] + timedelta(hours=9)
                    post["time_display"] = kst_time.strftime('%m.%d %H:%M')
                except:
                    post["time_display"] = "시간 정보 없음"
            else:
                post["time_display"] = "방금 전"

            # 댓글은 필요한 정보만 최소한으로 가져오기
            post["comments"] = []
            comments_docs = db.collection("posts").document(doc.id).collection("comments").limit(10).get()
            for c in comments_docs:
                c_data = c.to_dict()
                c_data["id"] = c.id
                post["comments"].append(c_data)
            posts.append(post)
        
        # 렌더링 후 메모리 즉시 청소
        response = render_template("index.html", posts=posts)
        del posts
        gc.collect() 
        return response
    except Exception as e:
        gc.collect()
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
    gc.collect()
    return redirect("/")

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

# 4. 신고 기능
@app.route("/report/post/<post_id>", methods=["POST"])
def report_post(post_id):
    db.collection("posts").document(post_id).update({
        "reported": True,
        "report_reason": request.form["reason"]
    })
    return redirect("/")

# 5. 관리자 기능 (비밀번호: 4357)
@app.route("/silver_admin_hidden_2464", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/silver_admin_hidden_2464")
        return "<script>alert('비번 틀림!'); history.back();</script>"
    
    if not session.get("admin"):
        return render_template("admin_login.html")
    
    # 관리자 페이지도 개수 제한
    docs = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(30).get()
    posts = []
    for doc in docs:
        post = doc.to_dict()
        post["id"] = doc.id
        posts.append(post)
    
    res = render_template("admin.html", posts=posts)
    gc.collect()
    return res

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

if __name__ == "__main__":
    # Render의 PORT 환경변수를 읽어오도록 설정
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
