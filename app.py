from flask import Flask, render_template, request, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta, datetime
import os, json
import gc

app = Flask(__name__)
app.secret_key = "silver_admin_secret_key_2026"
app.permanent_session_lifetime = timedelta(days=1)

# 1. Firebase 초기화 (Vercel 환경 변수 자동 인식 및 오류 방지 로직)
if not firebase_admin._apps:
    try:
        firebase_info = os.environ.get("FIREBASE_JSON")
        
        if firebase_info:
            # 환경 변수가 문자열인 경우 JSON으로 변환 (엄격하지 않은 모드 적용)
            cred_dict = json.loads(firebase_info, strict=False)
            
            # 💡 가장 중요한 부분: private_key 내의 실제 줄바꿈 문자를 복원함
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            
            cred = credentials.Certificate(cred_dict)
        else:
            # 로컬 작업 시 파일에서 읽어옴
            cred = credentials.Certificate("firebase_key.json")
            
        firebase_admin.initialize_app(cred)
        print("✅ 파이어베이스 연결 성공!")
    except Exception as e:
        print(f"❌ 파이어베이스 초기화 실패: {e}")

db = firestore.client()
ADMIN_PASSWORD = "4357"

# 2. 메인 페이지
@app.route("/")
def index():
    try:
        posts_ref = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(30)
        posts = []
        docs = posts_ref.get()
        
        for doc in docs:
            post = doc.to_dict()
            post["id"] = doc.id
            
            if "created" in post and post["created"]:
                try:
                    kst_time = post["created"] + timedelta(hours=9)
                    post["time_display"] = kst_time.strftime('%Y-%m-%d %H:%M')
                except:
                    post["time_display"] = "시간 정보 없음"
            else:
                post["time_display"] = "방금 전"

            post["comments"] = []
            comments_docs = db.collection("posts").document(doc.id).collection("comments").order_by("created").limit(20).get()
            for c in comments_docs:
                c_data = c.to_dict()
                c_data["id"] = c.id
                post["comments"].append(c_data)
            posts.append(post)
        
        response = render_template("index.html", posts=posts)
        del posts
        gc.collect() 
        return response
    except Exception as e:
        gc.collect()
        return f"서버 연결 오류: {e}. 파이어베이스 설정을 다시 확인해주세요."

# 3. 글쓰기 및 댓글 작성
@app.route("/submit", methods=["POST"])
def submit():
    content = request.form.get("content", "").strip()
    nickname = request.form.get("nickname", "익명").strip()
    if content:
        db.collection("posts").add({
            "nickname": nickname,
            "content": content,
            "reported": False,
            "created": firestore.SERVER_TIMESTAMP
        })
    gc.collect()
    return redirect("/")

@app.route("/comment/<post_id>", methods=["POST"])
def comment(post_id):
    content = request.form.get("content", "").strip()
    nickname = request.form.get("nickname", "익명").strip()
    if content:
        db.collection("posts").document(post_id).collection("comments").add({
            "nickname": nickname,
            "content": content,
            "reported": False,
            "created": firestore.SERVER_TIMESTAMP
        })
    gc.collect()
    return redirect("/")

# 4. 신고 및 관리자 기능
@app.route("/report/post/<post_id>", methods=["POST"])
def report_post(post_id):
    db.collection("posts").document(post_id).update({
        "reported": True,
        "report_reason": request.form.get("reason", "사유 없음")
    })
    return redirect("/")

@app.route("/silver_admin_hidden_2464", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        return "<script>alert('비밀번호가 틀렸습니다.'); history.back();</script>"
    
    if not session.get("admin"):
        return render_template("admin_login.html")
    
    docs = db.collection("posts").order_by("created", direction=firestore.Query.DESCENDING).limit(50).get()
    posts = []
    for doc in docs:
        post = doc.to_dict()
        post["id"] = doc.id
        posts.append(post)
    
    res = render_template("admin.html", posts=posts)
    gc.collect()
    return res

@app.route("/admin/delete/post/<post_id>", methods=["POST"])
def delete_post(post_id):
    if not session.get("admin"): return redirect("/")
    db.collection("posts").document(post_id).delete()
    return redirect(url_for("admin"))

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect("/")

# Vercel 배포를 위한 설정
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
