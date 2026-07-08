import os
import json
import time
import requests
from datetime import datetime, timezone

APIFY_TOKEN = os.environ.get("APIFY_TOKEN")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
BASE = "https://api.apify.com/v2"

INSTAGRAM_HASHTAGS = [
    "kbeauty", "koreanfashion", "koreanskincare",
    "koreanbeauty", "kbeautyhaul", "seoullife"
]
TIKTOK_KEYWORDS = [
    "kbeauty", "korean skincare", "grwm korean", "kpop style"
]
YOUTUBE_KEYWORDS = [
    "korean skincare routine", "kbeauty haul",
    "korea travel shopping", "k beauty review"
]
X_KEYWORDS = [
    "kbeauty", "korean skincare", "koreanbeauty", "seoulbeauty"
]
AMAZON_KEYWORDS = [
    "korean skin care", "snail mucin serum",
    "cica cream", "korean sunscreen"
]
GOOGLE_TRENDS_KEYWORDS = [
    "korean skincare", "k-beauty brands", "cica cream",
    "where to buy korean skincare", "korean beauty products"
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
    "us": "US",
    "eu": "GB",
    "me": "AE",
    "sea": "TH"
}

GAP_BRAND_QUERIES = {
    "us": [
        {"brand": "Skin1004", "query": "where to buy skin1004 us"},
        {"brand": "Round Lab", "query": "round lab usa"},
        {"brand": "Isntree", "query": "isntree where to buy"},
        {"brand": "Anua", "query": "where to buy anua us"},
        {"brand": "Numbuzin", "query": "numbuzin where to buy"},
    ],
    "eu": [
        {"brand": "Anua", "query": "anua uk"},
        {"brand": "Round Lab", "query": "round lab europe"},
        {"brand": "Skin1004", "query": "skin1004 uk"},
        {"brand": "Mixsoon", "query": "mixsoon europe"},
        {"brand": "Tocobo", "query": "tocobo europe"},
    ],
    "me": [
        {"brand": "Tamburins", "query": "tamburins uae"},
        {"brand": "Anua", "query": "anua saudi arabia"},
        {"brand": "Skin1004", "query": "skin1004 middle east"},
        {"brand": "Abib", "query": "abib uae"},
    ],
    "sea": [
        {"brand": "Romand", "query": "romand thailand"},
        {"brand": "Beauty of Joseon", "query": "beauty of joseon malaysia"},
        {"brand": "Anua", "query": "anua vietnam"},
        {"brand": "Numbuzin", "query": "numbuzin thailand"},
    ]
}

INFLUENCER_HASHTAGS = {
    "us": ["kbeautyus", "koreanskincare", "kbeautyreview"],
    "eu": ["kbeautyuk", "kbeautyeurope", "koreanbeautyuk"],
    "me": ["kbeautyarab", "koreanskincarearabia", "kbeautydubai"],
    "sea": ["kbeautythailand", "kbeautyvietnam", "koreanskincareph"]
}

def run_actor(actor_id, input_data, timeout=120, memory=512):
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
            params={**params, "limit": 50}, timeout=30
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
            "hashtags": [tag], "resultsLimit": 15
        })
        for item in data[:15]:
            results.append({
                "platform": "instagram", "hashtag": tag,
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
                "owner": item.get("ownerUsername", ""),
                "url": item.get("url", ""),
            })
    print(f"  → {len(results)}개")
    return results

def collect_tiktok():
    print("🎵 TikTok 수집 중...")
    results = []
    for kw in TIKTOK_KEYWORDS:
        data = run_actor("clockworks/tiktok-scraper", {
            "hashtags": [kw], "resultsPerPage": 10
        })
        for item in data[:10]:
            results.append({
                "platform": "tiktok", "keyword": kw,
                "plays": item.get("playCount", 0),
                "likes": item.get("diggCount", 0),
                "shares": item.get("shareCount", 0),
                "author": item.get("authorMeta", {}).get("name", ""),
                "author_fans": item.get("authorMeta", {}).get("fans", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_youtube():
    print("▶️  YouTube 수집 중...")
    results = []
    for kw in YOUTUBE_KEYWORDS:
        data = run_actor("streamers/youtube-scraper", {
            "searchKeywords": kw, "maxResults": 8, "sortBy": "relevance"
        })
        for item in data[:8]:
            results.append({
                "platform": "youtube", "keyword": kw,
                "title": item.get("title", ""),
                "views": item.get("viewCount", 0),
                "likes": item.get("likes", 0),
                "channel": item.get("channelName", ""),
                "channel_url": item.get("channelUrl", ""),
            })
    print(f"  → {len(results)}개")
    return results

def collect_x():
    print("✖️  X(Twitter) 수집 중...")
    results = []
    for kw in X_KEYWORDS:
        data = run_actor("apidojo/tweet-scraper", {
            "searchTerms": [kw], "maxTweets": 10, "onlyVerifiedUsers": False
        })
        for item in data[:10]:
            results.append({
                "platform": "x", "keyword": kw,
                "text": item.get("text", "")[:100],
                "likes": item.get("likeCount", 0),
                "retweets": item.get("retweetCount", 0),
                "author": item.get("author", {}).get("userName", ""),
                "author_followers": item.get("author", {}).get("followers", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_amazon():
    print("📦 Amazon 수집 중...")
    results = []
    for kw in AMAZON_KEYWORDS:
        data = run_actor("igview-owner/amazon-search-scraper", {
            "keyword": kw, "maxItems": 8, "country": "US"
        })
        for item in data[:8]:
            results.append({
                "platform": "amazon", "keyword": kw,
                "title": item.get("title", "")[:80],
                "rating": item.get("rating", 0),
                "reviews": item.get("reviewsCount", 0),
            })
    print(f"  → {len(results)}개")
    return results

def collect_google_trends(geo="", label="글로벌"):
    print(f"🔍 Google Trends 수집 중... ({label})")
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=0)
        results = []
        pytrends.build_payload(GOOGLE_TRENDS_KEYWORDS[:5], timeframe="now 7-d", geo=geo)
        interest = pytrends.interest_over_time()
        if not interest.empty:
            for kw in GOOGLE_TRENDS_KEYWORDS[:5]:
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
    print("🌍 권역별 브랜드 트렌드 수집 중...")
    region_brands = {}
    try:
        from pytrends.request import TrendReq
        for region, geo in REGION_GEO.items():
            print(f"  → {region.upper()} ({geo})...")
            brand_scores = {}
            chunks = [BRAND_KEYWORDS[i:i+5] for i in range(0, len(BRAND_KEYWORDS), 5)]
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
                    continue
            top = sorted(brand_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            region_brands[region] = [{"name": k, "score": v} for k, v in top]
            print(f"    → {[b['name'] for b in region_brands[region]]}")
    except Exception as e:
        print(f"  [SKIP] 권역별 브랜드: {e}")
    return region_brands

def collect_gap_brands():
    print("🔍 구매처 공백 브랜드 수집 중...")
    gap_data = {}
    try:
        from pytrends.request import TrendReq
        for region, queries in GAP_BRAND_QUERIES.items():
            print(f"  → {region.upper()}...")
            region_gaps = []
            for q in queries:
                try:
                    pytrends = TrendReq(hl="en-US", tz=0)
                    pytrends.build_payload([q["query"]], timeframe="now 30-d", geo="")
                    interest = pytrends.interest_over_time()
                    if not interest.empty and q["query"] in interest.columns:
                        score = int(interest[q["query"]].mean())
                        if score > 0:
                            region_gaps.append({
                                "brand": q["brand"],
                                "query": q["query"],
                                "score": score,
                                "search": f"\"{q['query']}\" 관심도 {score}",
                                "reason": "글로벌 구매처 부재 — 직구만 가능"
                            })
                    time.sleep(1)
                except Exception as e:
                    print(f"    [SKIP] {q['query']}: {e}")
                    continue
            region_gaps.sort(key=lambda x: x["score"], reverse=True)
            gap_data[region] = region_gaps[:4]
            print(f"    → {[g['brand'] for g in gap_data[region]]}")
    except Exception as e:
        print(f"  [SKIP] 구매처 공백: {e}")
    return gap_data

def collect_influencers():
    print("👤 인플루언서 수집 중...")
    influencers = {"us": [], "eu": [], "me": [], "sea": []}
    for region, hashtags in INFLUENCER_HASHTAGS.items():
        print(f"  → {region.upper()}...")
        candidates = {}
        for tag in hashtags:
            data = run_actor("apify/instagram-hashtag-scraper", {
                "hashtags": [tag], "resultsLimit": 30
            })
            for item in data[:30]:
                owner = item.get("ownerUsername", "")
                if not owner:
                    continue
                likes = item.get("likesCount", 0)
                comments = item.get("commentsCount", 0)
                followers = item.get("ownerFullName", "")
                if owner not in candidates:
                    candidates[owner] = {
                        "handle": f"@{owner}",
                        "platform": "instagram",
                        "total_likes": 0,
                        "total_comments": 0,
                        "post_count": 0,
                        "region": region,
                    }
                candidates[owner]["total_likes"] += likes
                candidates[owner]["total_comments"] += comments
                candidates[owner]["post_count"] += 1

        # 인게이지먼트 계산 및 상위 5명 추출
        scored = []
        for owner, data in candidates.items():
            if data["post_count"] < 2:
                continue
            avg_likes = data["total_likes"] / data["post_count"]
            avg_comments = data["total_comments"] / data["post_count"]
            # 팔로워 추정치 (평균 좋아요 기반)
            est_followers = avg_likes * 20
            eng_rate = round((avg_likes + avg_comments) / max(est_followers, 1) * 100, 1)
            scored.append({
                "handle": data["handle"],
                "platform": "instagram",
                "niche": "K-뷰티",
                "followers": f"{int(est_followers/1000)}K" if est_followers >= 1000 else str(int(est_followers)),
                "avg_likes": f"{int(avg_likes/1000)}K" if avg_likes >= 1000 else str(int(avg_likes)),
                "engagement": min(eng_rate, 30.0),
                "contact": eng_rate >= 5.0,
                "score": avg_likes + avg_comments * 3,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        influencers[region] = scored[:5]
        print(f"    → {region}: {[i['handle'] for i in influencers[region]]}")

    return influencers

def aggregate(instagram, tiktok, youtube, x_data, amazon, google):
    brand_counts = {b: 0 for b in BRAND_KEYWORDS}
    ingredient_counts = {i: 0 for i in INGREDIENT_KEYWORDS}

    for item in instagram:
        tag = item["hashtag"].lower()
        for brand in BRAND_KEYWORDS:
            if brand.replace(" ", "") in tag.replace(" ", ""):
                brand_counts[brand] += max(item.get("likes", 0) // 100, 1)

    for item in tiktok:
        kw = item["keyword"].lower()
        for brand in BRAND_KEYWORDS:
            if brand.replace(" ", "") in kw.replace(" ", ""):
                brand_counts[brand] += max(item.get("likes", 0) // 1000, 1)
        text = kw
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("likes", 0) // 1000, 1)

    for item in youtube:
        text = (item.get("title", "") + " " + item.get("keyword", "")).lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("views", 0) // 10000, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("views", 0) // 10000, 1)

    for item in x_data:
        text = item.get("text", "").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("likes", 0) // 10, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("likes", 0) // 10, 1)

    for item in amazon:
        text = item.get("title", "").lower()
        for brand in BRAND_KEYWORDS:
            if brand in text:
                brand_counts[brand] += max(item.get("reviews", 0) // 100, 1)
        for ing in INGREDIENT_KEYWORDS:
            if ing in text:
                ingredient_counts[ing] += max(item.get("reviews", 0) // 100, 1)

    for item in google:
        kw = item["keyword"].lower()
        for ing in INGREDIENT_KEYWORDS:
            if ing in kw:
                ingredient_counts[ing] += item.get("interest", 0)

    where_to_buy = sum(
        i.get("interest", 0) for i in google
        if "where to buy" in i.get("keyword", "")
    ) * 100 or 0

    top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_ingredients = sorted(ingredient_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # 시즌 시그널 동적 생성
    signals = []
    month = datetime.now(timezone.utc).month
    if month == 1 or month == 2:
        signals.append({"type": "sig-season", "badge": "시즌", "text": "겨울 보습 시즌 — 크림·세럼 수요 피크, 선물세트 기획 적기", "dday": "진행 중"})
    elif month == 3 or month == 4:
        signals.append({"type": "sig-season", "badge": "시즌", "text": "봄 스킨케어 전환 — 가벼운 수분 제품·선케어 수요 상승", "dday": "진행 중"})
    elif month == 5 or month == 6:
        signals.append({"type": "sig-season", "badge": "시즌", "text": "여름 선케어 시즌 — SPF 제품 검색량 급증", "dday": "진행 중"})
        signals.append({"type": "sig-season", "badge": "시즌", "text": "Mother's Day / Father's Day — 선물세트 기획 적기", "dday": "5~6월"})
    elif month == 7 or month == 8:
        signals.append({"type": "sig-season", "badge": "시즌", "text": "Amazon Prime Day 시즌 — K-뷰티 비교 검색 급증", "dday": "진행 중"})
        signals.append({"type": "sig-season", "badge": "시즌", "text": "Summer Skincare — 선케어·수분 케어 수요 피크", "dday": "7~8월"})
    elif month == 9 or month == 10:
        signals.append({"type": "sig-season", "badge": "시즌", "text": "가을 스킨케어 전환 — 보습·장벽 케어 수요 상승", "dday": "진행 중"})
    elif month >= 11:
        signals.append({"type": "sig-season", "badge": "시즌", "text": "Black Friday / Cyber Monday — 연중 최대 K-뷰티 구매 피크", "dday": "준비 시작"})
        signals.append({"type": "sig-season", "badge": "시즌", "text": "Holiday Gift Sets — 선물세트 기획·MD 협의 시작", "dday": "11~12월"})

    # 급상승 성분
    top_ing_list = sorted([(k,v) for k,v in ingredient_counts.items() if v>0], key=lambda x: x[1], reverse=True)
    if top_ing_list:
        top_ing = top_ing_list[0]
        signals.append({"type": "sig-ingredient", "badge": "성분", "text": f"{top_ing[0].title()} 바이럴 — SNS 전반 언급량 급증 (스코어: {top_ing[1]})", "dday": "진행 중"})

    # 급상승 브랜드
    top_brand_list = sorted([(k,v) for k,v in brand_counts.items() if v>0], key=lambda x: x[1], reverse=True)
    if top_brand_list:
        top_b = top_brand_list[0]
        signals.append({"type": "sig-social", "badge": "브랜드", "text": f"{top_b[0].title()} — 이번 주 SNS 언급 1위 (스코어: {top_b[1]})", "dday": "이번 주"})

    if not signals:
        signals = [{"type": "sig-social", "badge": "소셜", "text": "데이터 수집 중 — 잠시 후 업데이트됩니다", "dday": "-"}]

    return {
        "top_brands": [{"name": k, "score": v} for k, v in top_brands if v > 0],
        "top_ingredients": [{"name": k, "score": v} for k, v in top_ingredients if v > 0],
        "signals": signals,
        "where_to_buy": where_to_buy,
    }

def main():
    print(f"\n🚀 K-Beauty 전체 수집 시작 — {TODAY}\n")

    instagram   = collect_instagram()
    tiktok      = collect_tiktok()
    youtube     = collect_youtube()
    x_data      = collect_x()
    amazon      = collect_amazon()
    google      = collect_google_trends(geo="", label="글로벌")
    agg         = aggregate(instagram, tiktok, youtube, x_data, amazon, google)
    region_brands = collect_region_brands()
    gap_brands    = collect_gap_brands()
    influencers   = collect_influencers()

    total = len(instagram)+len(tiktok)+len(youtube)+len(x_data)+len(amazon)+len(google)

    report = {
        "date": TODAY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_keywords": total,
            "platforms": 6,
            "where_to_buy_search": agg["where_to_buy"],
        },
        "platforms": {
            "instagram": {"total": len(instagram), "top_hashtags": list(set([i["hashtag"] for i in instagram]))[:6]},
            "tiktok":    {"total": len(tiktok),    "top_keywords": list(set([i["keyword"] for i in tiktok]))[:5]},
            "youtube":   {"total": len(youtube),   "top_keywords": list(set([i["keyword"] for i in youtube]))[:5]},
            "x":         {"total": len(x_data),    "top_keywords": list(set([i["keyword"] for i in x_data]))[:5]},
            "amazon":    {"total": len(amazon),    "top_keywords": list(set([i["keyword"] for i in amazon]))[:5]},
            "google_trends": {"total": len(google), "keywords": [i["keyword"] for i in google]},
        },
        "brands": agg["top_brands"],
        "ingredients": agg["top_ingredients"],
        "signals": agg["signals"],
        "region_brands": region_brands,
        "gap_brands": gap_brands,
        "influencers": influencers,
        "raw": {
            "instagram": instagram[:30],
            "tiktok": tiktok[:30],
            "youtube": youtube[:20],
            "x": x_data[:20],
            "amazon": amazon[:20],
            "google": google
        }
    }

    os.makedirs("data", exist_ok=True)
    filepath = f"data/{TODAY}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open("data/latest.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료! {filepath}")
    print(f"   브랜드: {len(agg['top_brands'])}개")
    print(f"   성분: {len(agg['top_ingredients'])}개")
    print(f"   시그널: {len(agg['signals'])}개")
    print(f"   권역별 브랜드: {list(region_brands.keys())}")
    print(f"   구매처 공백: {list(gap_brands.keys())}")
    print(f"   인플루언서: {list(influencers.keys())}")
    print(f"   총 수집: {total}개")

if __name__ == "__main__":
    main()
