import os
import json
import time
import re
import requests
from datetime import datetime, timezone
from collections import Counter

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
NOW = datetime.now(timezone.utc)
BASE = "https://api.apify.com/v2"

# ── 키워드 설정 ────────────────────────────────────────────
INSTAGRAM_HASHTAGS = [
    "kbeauty", "koreanskincare", "koreanbeauty", "kbeautyhaul"
]
TIKTOK_KEYWORDS = [
    "kbeauty", "korean skincare", "kpop style"
]
YOUTUBE_KEYWORDS = [
    "korean skincare routine", "kbeauty haul", "k beauty review"
]
X_KEYWORDS = [
    "kbeauty", "korean skincare"
]
AMAZON_KEYWORDS = [
    "korean skin care", "snail mucin serum", "cica cream"
]
GOOGLE_TRENDS_KEYWORDS = [
    "korean skincare", "cica cream",
    "where to buy korean skincare", "korean beauty products"
]
XIAOHONGSHU_KEYWORDS = [
    "kbeauty", "korean skincare", "Anua", "Cosrx"
]
REDDIT_SUBREDDITS = [
    "SkincareAddiction", "AsianBeauty", "kbeauty"
]
BRAND_KEYWORDS = [
    "anua", "cosrx", "laneige", "beauty of joseon", "tamburins",
    "round lab", "skin1004", "mardi mercredi", "sulwhasoo", "innisfree",
    "purito", "isntree", "romand", "etude", "medicube", "biodance",
    "some by mi", "tocobo", "abib", "numbuzin"
]
INGREDIENT_KEYWORDS = [
    "centella", "cica", "niacinamide", "snail mucin", "bakuchiol",
    "azelaic acid", "ceramide", "vitamin c", "hyaluronic acid",
    "retinol", "propolis", "tranexamic acid", "peptide"
]

REGION_GEO = {
    "us": "US", "eu": "GB", "me": "AE",
    "zh": "SG", "sea": "TH"
}

# 구매처 공백 — 권역당 2개로 축소
GAP_BRAND_QUERIES = {
    "us":  [{"brand": "Skin1004", "query": "Skin1004 USA"},
            {"brand": "Anua", "query": "Anua USA"}],
    "eu":  [{"brand": "Anua", "query": "Anua Europe"},
            {"brand": "Round Lab", "query": "Round Lab Europe"}],
    "me":  [{"brand": "Tamburins", "query": "Tamburins UAE"},
            {"brand": "Anua", "query": "Anua Middle East"}],
    "zh":  [{"brand": "Anua", "query": "Anua Singapore"},
            {"brand": "Tamburins", "query": "Tamburins Singapore"}],
    "sea": [{"brand": "Romand", "query": "Romand Thailand"},
            {"brand": "Anua", "query": "Anua Vietnam"}]
}

INFLUENCER_HASHTAGS = {
    "us":  ["kbeautyus", "koreanskincare"],
    "eu":  ["kbeautyuk", "kbeautyeurope"],
    "me":  ["kbeautydubai", "kbeautyarab"],
    "zh":  ["kbeautysingapore", "koreanbeautysg"],
    "sea": ["kbeautythailand", "kbeautyvietnam"]
}

REGION_INFO = {
    "us":  {"flag": "🇺🇸", "title": "미주 — 미국 / 캐나다", "sub": "TikTok 트렌드 진원지 · K-뷰티 최대 시장", "priority": "주력"},
    "eu":  {"flag": "🇬🇧", "title": "유럽 — 영국 / 프랑스 / 독일", "sub": "클린뷰티 민감 · EU 규제 인식 높음", "priority": "주력"},
    "me":  {"flag": "🌙", "title": "중동 — UAE / 사우디 / 쿠웨이트", "sub": "할랄 인증 중요 · 럭셔리 선호", "priority": "주력"},
    "zh":  {"flag": "🇨🇳", "title": "중화권 — 싱가포르 / 홍콩 / 대만", "sub": "샤오홍슈 중심 · 왕훙 인플루언서", "priority": "주력"},
    "sea": {"flag": "🌏", "title": "동남아 — 태국 / 베트남 / 말레이시아", "sub": "K-팝 연동 강함 · 가성비 민감", "priority": "주력"}
}

def run_actor(actor_id, input_data, timeout=120, memory=256):
    params = {"token": APIFY_TOKEN}
    actor_id_safe = actor_id.replace("/", "~")
    try:
        run_resp = requests.post(
            f"{BASE}/acts/{actor_id_safe}/runs",
            json={**input_data, "memory": memory},
            params=params, timeout=30
        )
        run_resp.raise_for_status()
        run_data = run_resp.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]
        for _ in range(timeout // 5):
            status_resp = requests.get(f"{BASE}/actor-runs/{run_id}", params=params, timeout=10)
            status = status_resp.json()["data"]["status"]
            if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break
            time.sleep(5)
        if status != "SUCCEEDED":
            print(f"  [SKIP] {actor_id}: status={status}")
            return []
        items_resp = requests.get(
            f"{BASE}/datasets/{dataset_id}/items",
            params={**params, "limit": 30}, timeout=30
        )
        return items_resp.json()
    except Exception as e:
        print(f"  [SKIP] {actor_id}: {e}")
        return []

def collect_instagram():
    print("📸 Instagram 수집 중...")
    results = []
    for tag in INSTAGRAM_HASHTAGS:
        data = run_actor("apify/instagram-hashtag-scraper", {
            "hashtags": [tag], "resultsLimit": 10
        })
        for item in data[:10]:
            results.append({
                "platform": "instagram", "hashtag": tag,
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
                "owner": item.get("ownerUsername", ""),
                "caption_hashtags": item.get("hashtags", []),
            })
    print(f"  → {len(results)}개")
    return results

def collect_tiktok():
    print("🎵 TikTok 수집 중...")
    results = []
    for kw in TIKTOK_KEYWORDS:
        data = run_actor("clockworks/tiktok-scraper", {
            "hashtags": [kw], "resultsPerPage": 8
        })
        for item in data[:8]:
            results.append({
                "platform": "tiktok", "keyword": kw,
                "plays": item.get("playCount", 0),
                "likes": item.get("diggCount", 0),
                "hashtags": [h.get("name","") for h in item.get("hashtags", [])],
                "text": item.get("text", ""),
            })
    print(f"  → {len(results)}개")
    return results

def collect_youtube():
    print("▶️  YouTube 수집 중...")
    results = []
    for kw in YOUTUBE_KEYWORDS:
        data = run_actor("streamers/youtube-scraper", {
            "searchKeywords": kw, "maxResults": 5, "sortBy": "relevance"
        })
        for item in data[:5]:
            results.append({
                "platform": "youtube", "keyword": kw,
                "title": item.get("title", ""),
                "views": item.get("viewCount", 0),
                "likes": item.get("likes", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_x():
    print("✖️  X(Twitter) 수집 중...")
    results = []
    all_hashtags = []
    for kw in X_KEYWORDS:
        data = run_actor("apidojo/tweet-scraper", {
            "searchTerms": [kw], "maxTweets": 8, "onlyVerifiedUsers": False
        })
        for item in data[:8]:
            text = item.get("text", "")
            hashtags = re.findall(r'#(\w+)', text)
            all_hashtags.extend([h.lower() for h in hashtags if len(h) > 2])
            results.append({
                "platform": "x", "keyword": kw,
                "text": text[:150],
                "likes": item.get("likeCount", 0),
                "retweets": item.get("retweetCount", 0),
                "hashtags": hashtags,
            })
    top_hashtags = [tag for tag, _ in Counter(all_hashtags).most_common(8)
                    if tag not in ["kbeauty","korean","beauty","skincare","skin"]]
    print(f"  → {len(results)}개 · 해시태그: {top_hashtags[:5]}")
    return results, top_hashtags

def collect_amazon():
    print("📦 Amazon 수집 중...")
    results = []
    for kw in AMAZON_KEYWORDS:
        data = run_actor("igview-owner/amazon-search-scraper", {
            "keyword": kw, "maxItems": 5, "country": "US"
        })
        for item in data[:5]:
            results.append({
                "platform": "amazon", "keyword": kw,
                "title": item.get("title", "")[:80],
                "rating": item.get("rating", 0),
                "reviews": item.get("reviewsCount", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_xiaohongshu():
    print("📕 샤오홍슈 수집 중...")
    results = []
    for kw in XIAOHONGSHU_KEYWORDS:
        data = run_actor("zhorex/rednote-xiaohongshu-scraper", {
            "mode": "search", "searchQuery": kw,
            "maxResults": 8, "filterByMinLikes": 50
        })
        for item in data[:8]:
            brand_found = None
            title = item.get("title", "").lower()
            for brand in BRAND_KEYWORDS:
                if brand in title:
                    brand_found = brand
                    break
            results.append({
                "platform": "xiaohongshu", "keyword": kw,
                "title": item.get("title", "")[:80],
                "likes": item.get("likes", 0),
                "comments": item.get("comments", 0),
                "brand_mentioned": brand_found,
            })
    print(f"  → {len(results)}개")
    return results

def collect_reddit():
    print("🔴 Reddit 수집 중...")
    results = []
    trending_topics = []
    for subreddit in REDDIT_SUBREDDITS:
        data = run_actor("clearpath/reddit-post-comments-b", {
            "subreddit": subreddit, "sort": "hot",
            "maxPosts": 3, "maxComments": 15, "sortComments": "top"
        })
        for item in data[:18]:
            text = (item.get("body", "") or item.get("text", "") or "").lower()
            if not text:
                continue
            brands_found = [b for b in BRAND_KEYWORDS if b in text]
            ings_found = [i for i in INGREDIENT_KEYWORDS if i in text]
            gap_signal = any(kw in text for kw in [
                "where to buy", "can't find", "out of stock",
                "not available", "sold out"
            ])
            words = re.findall(r'\b[a-z]{4,}\b', text)
            trending_topics.extend(words)
            results.append({
                "platform": "reddit", "subreddit": subreddit,
                "text": text[:200], "score": item.get("score", 0),
                "brands_mentioned": brands_found,
                "ingredients_mentioned": ings_found,
                "gap_signal": gap_signal,
            })
    print(f"  → {len(results)}개")
    return results, trending_topics

def collect_google_trends(geo="", label="글로벌"):
    print(f"🔍 Google Trends 수집 중... ({label})")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=0)
        results = []
        pytrends.build_payload(GOOGLE_TRENDS_KEYWORDS[:4], timeframe="now 7-d", geo=geo)
        interest = pytrends.interest_over_time()
        if not interest.empty:
            for kw in GOOGLE_TRENDS_KEYWORDS[:4]:
                if kw in interest.columns:
                    results.append({
                        "platform": "google_trends", "keyword": kw,
                        "interest": int(interest[kw].mean()), "geo": geo or "global"
                    })
        print(f"  → {len(results)}개")
        return results
    except Exception as e:
        print(f"  [SKIP] Google Trends ({label}): {e}")
        return []

def collect_region_brands():
    """권역별 브랜드 — 주 2회만 실행 (월·목)"""
    day_of_week = NOW.weekday()  # 0=월, 3=목
    if day_of_week not in [0, 3]:
        print(f"🌍 권역별 브랜드 — 오늘은 SKIP (월·목만 실행, 오늘은 {['월','화','수','목','금','토','일'][day_of_week]})")
        return {}

    print("🌍 권역별 브랜드 트렌드 수집 중...")
    region_brands = {}
    try:
        from pytrends.request import TrendReq
        # 상위 10개 브랜드만, 5개씩 2 chunk
        top_brands = BRAND_KEYWORDS[:10]
        chunks = [top_brands[i:i+5] for i in range(0, len(top_brands), 5)]
        for region, geo in REGION_GEO.items():
            print(f"  → {region.upper()} ({geo})...")
            brand_scores = {}
            for chunk in chunks:
                try:
                    pytrends = TrendReq(hl="en-US", tz=0)
                    pytrends.build_payload(chunk, timeframe="now 7-d", geo=geo)
                    interest = pytrends.interest_over_time()
                    if not interest.empty:
                        for brand in chunk:
                            if brand in interest.columns:
                                score = int(interest[brand].mean())
                                if score > 0:
                                    brand_scores[brand] = score
                    time.sleep(2)
                except Exception as e:
                    print(f"    [SKIP] {chunk}: {e}")
            top = sorted(brand_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            region_brands[region] = [{"name": k, "score": v} for k, v in top]
            print(f"    → {[b['name'] for b in region_brands[region]]}")
    except Exception as e:
        print(f"  [SKIP]: {e}")
    return region_brands

def collect_gap_brands(reddit_data):
    """구매처 공백 — 주 2회만 실행 (월·목)"""
    day_of_week = NOW.weekday()
    if day_of_week not in [0, 3]:
        print(f"🔍 구매처 공백 — 오늘은 SKIP (월·목만 실행)")
        return {}

    print("🔍 구매처 공백 브랜드 수집 중...")
    gap_data = {}
    reddit_gaps = {}
    for item in reddit_data:
        if item.get("gap_signal") and item.get("brands_mentioned"):
            for brand in item["brands_mentioned"]:
                reddit_gaps[brand] = reddit_gaps.get(brand, 0) + max(item.get("score", 1), 1)
    try:
        from pytrends.request import TrendReq
        for region, queries in GAP_BRAND_QUERIES.items():
            region_gaps = []
            for q in queries:
                try:
                    pytrends = TrendReq(hl="en-US", tz=0)
                    pytrends.build_payload([q["query"]], timeframe="now 30-d", geo="")
                    interest = pytrends.interest_over_time()
                    score = 0
                    if not interest.empty and q["query"] in interest.columns:
                        score = int(interest[q["query"]].mean())
                    reddit_score = reddit_gaps.get(q["brand"].lower(), 0)
                    total_score = score + (reddit_score * 10)
                    if total_score > 0:
                        region_gaps.append({
                            "brand": q["brand"], "query": q["query"],
                            "score": total_score,
                            "search": f"\"{q['query']}\" 관심도 {score}",
                            "reason": "글로벌 구매처 부재 — 직구만 가능",
                        })
                    time.sleep(1)
                except Exception as e:
                    print(f"    [SKIP] {q['query']}: {e}")
            region_gaps.sort(key=lambda x: x["score"], reverse=True)
            gap_data[region] = region_gaps[:3]
    except Exception as e:
        print(f"  [SKIP]: {e}")
    return gap_data

def collect_influencers():
    """인플루언서 — 주 2회만 실행 (화·금)"""
    day_of_week = NOW.weekday()
    if day_of_week not in [1, 4]:
        print(f"👤 인플루언서 — 오늘은 SKIP (화·금만 실행)")
        return {}

    print("👤 인플루언서 수집 중...")
    influencers = {r: [] for r in REGION_GEO.keys()}
    for region, hashtags in INFLUENCER_HASHTAGS.items():
        print(f"  → {region.upper()}...")
        candidates = {}
        for tag in hashtags:
            data = run_actor("apify/instagram-hashtag-scraper", {
                "hashtags": [tag], "resultsLimit": 20
            })
            for item in data[:20]:
                owner = item.get("ownerUsername", "")
                if not owner:
                    continue
                if any('\uac00' <= c <= '\ud7a3' for c in owner):
                    continue
                likes = item.get("likesCount", 0)
                comments = item.get("commentsCount", 0)
                if owner not in candidates:
                    candidates[owner] = {"handle": f"@{owner}", "platform": "instagram",
                                        "total_likes": 0, "total_comments": 0, "post_count": 0}
                candidates[owner]["total_likes"] += likes
                candidates[owner]["total_comments"] += comments
                candidates[owner]["post_count"] += 1
        scored = []
        for owner, d in candidates.items():
            if d["post_count"] < 2:
                continue
            avg_likes = d["total_likes"] / d["post_count"]
            avg_comments = d["total_comments"] / d["post_count"]
            est_followers = avg_likes * 20
            if est_followers < 10000:
                continue
            eng_rate = round((avg_likes + avg_comments) / max(est_followers, 1) * 100, 1)
            scored.append({
                "handle": d["handle"], "platform": "instagram", "niche": "K-뷰티",
                "followers": f"{int(est_followers/1000)}K",
                "avg_likes": f"{int(avg_likes/1000)}K" if avg_likes >= 1000 else str(int(avg_likes)),
                "engagement": min(eng_rate, 30.0),
                "contact": eng_rate >= 5.0,
                "score": avg_likes + avg_comments * 3,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        influencers[region] = scored[:5]
    return influencers

def collect_xiaohongshu_brands(xhs_data):
    brand_mentions = {}
    for item in xhs_data:
        brand = item.get("brand_mentioned")
        if brand:
            if brand not in brand_mentions:
                brand_mentions[brand] = {"mentions": 0, "total_likes": 0}
            brand_mentions[brand]["mentions"] += 1
            brand_mentions[brand]["total_likes"] += item.get("likes", 0)
    result = []
    for brand, data in brand_mentions.items():
        score = data["mentions"] * 10 + data["total_likes"] // 100
        result.append({"name": brand, "score": score,
                       "mentions": data["mentions"], "total_likes": data["total_likes"]})
    return sorted(result, key=lambda x: x["score"], reverse=True)[:8]

def extract_sns_signals(instagram, tiktok, x_data, reddit_data, x_hashtags, reddit_topics, brand_counts, ingredient_counts):
    signals = []

    # Instagram 급상승 해시태그
    all_ig_tags = []
    for item in instagram:
        all_ig_tags.extend(item.get("caption_hashtags", []))
    ig_tag_counts = Counter([t.lower() for t in all_ig_tags if t and len(t) > 3])
    top_ig_tags = [t for t, c in ig_tag_counts.most_common(5)
                   if t not in ["kbeauty","koreanbeauty","koreanskincare","beauty","skincare"]]
    if top_ig_tags:
        signals.append({"type": "sig-social", "badge": "Instagram",
                        "text": f"인스타 급상승 해시태그 — #{' #'.join(top_ig_tags[:3])}", "dday": "이번 주"})

    # TikTok 바이럴
    all_tt_tags = []
    for item in tiktok:
        all_tt_tags.extend(item.get("hashtags", []))
    tt_tag_counts = Counter([t.lower() for t in all_tt_tags if t and len(t) > 3])
    top_tt_tags = [t for t, c in tt_tag_counts.most_common(5)
                   if t not in ["kbeauty","korean","beauty","skincare","grwm","fyp"]]
    if top_tt_tags:
        signals.append({"type": "sig-social", "badge": "TikTok",
                        "text": f"TikTok 바이럴 태그 — #{' #'.join(top_tt_tags[:3])}", "dday": "진행 중"})

    # X 트렌딩
    if x_hashtags:
        signals.append({"type": "sig-social", "badge": "X 트렌드",
                        "text": f"X(트위터) 급상승 — #{' #'.join(x_hashtags[:3])}", "dday": "오늘"})

    # Reddit 화제
    stop_words = {"that","this","with","have","from","they","what","your","been","will",
                  "just","like","skin","care","korean","beauty","product","good","really","also"}
    filtered = [w for w in reddit_topics if w not in stop_words and len(w) > 4]
    top_reddit = [w for w, c in Counter(filtered).most_common(10)
                  if w not in [b.replace(" ","") for b in BRAND_KEYWORDS]][:3]
    if top_reddit:
        signals.append({"type": "sig-news", "badge": "Reddit",
                        "text": f"Reddit 화제 키워드 — {', '.join(top_reddit)}", "dday": "이번 주"})

    # Reddit 구매처 공백
    gap_brands_reddit = {}
    for item in reddit_data:
        if item.get("gap_signal"):
            for brand in item.get("brands_mentioned", []):
                gap_brands_reddit[brand] = gap_brands_reddit.get(brand, 0) + max(item.get("score",1),1)
    if gap_brands_reddit:
        top_gap = max(gap_brands_reddit, key=gap_brands_reddit.get)
        signals.append({"type": "sig-news", "badge": "구매처",
                        "text": f"Reddit에서 '{top_gap.title()}' 구매처 문의 급증", "dday": "진행 중"})

    # 급상승 성분
    top_ing = sorted([(k,v) for k,v in ingredient_counts.items() if v>0], key=lambda x: x[1], reverse=True)
    if top_ing:
        signals.append({"type": "sig-ingredient", "badge": "성분",
                        "text": f"{top_ing[0][0].title()} — 이번 주 SNS 전반 언급 급증 (스코어: {top_ing[0][1]})", "dday": "진행 중"})

    # 급상승 브랜드
    top_brand = sorted([(k,v) for k,v in brand_counts.items() if v>0], key=lambda x: x[1], reverse=True)
    if top_brand:
        signals.append({"type": "sig-social", "badge": "브랜드",
                        "text": f"{top_brand[0][0].title()} — 이번 주 8개 플랫폼 언급 1위 (스코어: {top_brand[0][1]})", "dday": "이번 주"})

    if not signals:
        signals = [{"type": "sig-social", "badge": "소셜", "text": "데이터 수집 중 — 잠시 후 업데이트됩니다", "dday": "-"}]
    return signals

def extract_heatmap_data(brands):
    heatmap = []
    max_score = max([b["score"] for b in brands], default=1)
    for brand in brands[:5]:
        r = brand["score"] / max_score
        if r >= 0.8:
            pattern = ["#b5d4f4","#378add","#0c447c","#0c447c"]; label="급상승"; lc="#c0392b"
        elif r >= 0.6:
            pattern = ["#f0f0ec","#b5d4f4","#378add","#0c447c"]; label="상승세"; lc="#27ae60"
        elif r >= 0.4:
            pattern = ["#f0f0ec","#f0f0ec","#b5d4f4","#378add"]; label="보통"; lc="#888"
        elif r >= 0.2:
            pattern = ["#f0f0ec","#f0f0ec","#f0f0ec","#b5d4f4"]; label="낮음"; lc="#bbb"
        else:
            pattern = ["#f0f0ec","#f0f0ec","#f0f0ec","#f0f0ec"]; label="미미"; lc="#ccc"
        heatmap.append({"name": brand["name"], "score": brand["score"],
                        "pattern": pattern, "label": label, "label_color": lc})
    return heatmap

def aggregate(instagram, tiktok, youtube, x_data, amazon, google, reddit_data, xhs_data, x_hashtags, reddit_topics):
    brand_counts = {b: 0 for b in BRAND_KEYWORDS}
    ingredient_counts = {i: 0 for i in INGREDIENT_KEYWORDS}

    for item in instagram:
        tag = item["hashtag"].lower()
        for brand in BRAND_KEYWORDS:
            if brand.replace(" ","") in tag.replace(" ",""):
                brand_counts[brand] += max(item.get("likes",0)//100, 1)

    for item in tiktok:
        text = (item.get("text","")+" "+item.get("keyword","")).lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("likes",0)//1000, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("likes",0)//1000, 1)

    for item in youtube:
        text = (item.get("title","")+" "+item.get("keyword","")).lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("views",0)//10000, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("views",0)//10000, 1)

    for item in x_data:
        text = item.get("text","").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("likes",0)//10, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("likes",0)//10, 1)

    for item in amazon:
        text = item.get("title","").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("reviews",0)//100, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("reviews",0)//100, 1)

    for item in reddit_data:
        for brand in item.get("brands_mentioned",[]):
            brand_counts[brand] = brand_counts.get(brand,0) + max(item.get("score",1),1)
        for ing in item.get("ingredients_mentioned",[]):
            ingredient_counts[ing] = ingredient_counts.get(ing,0) + max(item.get("score",1),1)

    for item in xhs_data:
        brand = item.get("brand_mentioned")
        if brand and brand in brand_counts:
            brand_counts[brand] += max(item.get("likes",0)//50, 1)

    for item in google:
        kw = item["keyword"].lower()
        for ing in INGREDIENT_KEYWORDS:
            if ing in kw:
                ingredient_counts[ing] += item.get("interest",0)

    where_to_buy = sum(i.get("interest",0) for i in google
                       if "where to buy" in i.get("keyword","")) * 100 or 0

    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_ingredients = sorted(ingredient_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_brands_list = [{"name": k, "score": v} for k, v in top_brands if v > 0]

    signals = extract_sns_signals(instagram, tiktok, x_data, reddit_data,
                                   x_hashtags, reddit_topics, brand_counts, ingredient_counts)
    heatmap = extract_heatmap_data(top_brands_list)

    return {
        "top_brands": top_brands_list,
        "top_ingredients": [{"name": k, "score": v} for k, v in top_ingredients if v > 0],
        "signals": signals, "heatmap": heatmap, "where_to_buy": where_to_buy,
    }

def main():
    print(f"\n🚀 K-Beauty 수집 시작 — {TODAY} ({['월','화','수','목','금','토','일'][NOW.weekday()]})\n")

    instagram           = collect_instagram()
    tiktok              = collect_tiktok()
    youtube             = collect_youtube()
    x_data, x_hashtags = collect_x()
    amazon              = collect_amazon()
    xhs_data            = collect_xiaohongshu()
    reddit_data, reddit_topics = collect_reddit()
    google              = collect_google_trends(geo="", label="글로벌")
    agg                 = aggregate(instagram, tiktok, youtube, x_data, amazon,
                                    google, reddit_data, xhs_data, x_hashtags, reddit_topics)
    region_brands       = collect_region_brands()
    gap_brands          = collect_gap_brands(reddit_data)
    influencers         = collect_influencers()
    xhs_brands          = collect_xiaohongshu_brands(xhs_data)

    total = len(instagram)+len(tiktok)+len(youtube)+len(x_data)+len(amazon)+len(xhs_data)+len(reddit_data)+len(google)

    report = {
        "date": TODAY,
        "generated_at": NOW.isoformat(),
        "summary": {"total_keywords": total, "platforms": 8, "where_to_buy_search": agg["where_to_buy"]},
        "platforms": {
            "instagram":     {"total": len(instagram),  "top_hashtags": list(set([i["hashtag"] for i in instagram]))[:6]},
            "tiktok":        {"total": len(tiktok),     "top_keywords": list(set([i["keyword"] for i in tiktok]))[:5]},
            "youtube":       {"total": len(youtube),    "top_keywords": list(set([i["keyword"] for i in youtube]))[:5]},
            "x":             {"total": len(x_data),     "top_hashtags": x_hashtags[:6]},
            "amazon":        {"total": len(amazon),     "top_keywords": list(set([i["keyword"] for i in amazon]))[:5]},
            "google_trends": {"total": len(google),     "keywords": [i["keyword"] for i in google]},
            "xiaohongshu":   {"total": len(xhs_data),  "top_keywords": XIAOHONGSHU_KEYWORDS[:4], "brand_mentions": xhs_brands},
            "reddit":        {"total": len(reddit_data),"subreddits": REDDIT_SUBREDDITS},
        },
        "brands": agg["top_brands"],
        "ingredients": agg["top_ingredients"],
        "signals": agg["signals"],
        "heatmap": agg["heatmap"],
        "region_brands": region_brands,
        "gap_brands": gap_brands,
        "influencers": influencers,
        "region_info": REGION_INFO,
        "raw": {
            "instagram": instagram[:15], "tiktok": tiktok[:15],
            "youtube": youtube[:10], "x": x_data[:10],
            "amazon": amazon[:10], "xiaohongshu": xhs_data[:10],
            "reddit": reddit_data[:15], "google": google
        }
    }

    os.makedirs("data", exist_ok=True)
    filepath = f"data/{TODAY}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open("data/latest.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료! {filepath}")
    print(f"   브랜드: {len(agg['top_brands'])}개 / 성분: {len(agg['top_ingredients'])}개")
    print(f"   시그널: {len(agg['signals'])}개 / 히트맵: {len(agg['heatmap'])}개")
    print(f"   총 수집: {total}개")

if __name__ == "__main__":
    main()
