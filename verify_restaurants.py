#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高德地图餐馆真实性验证脚本
使用方法: python3 verify_restaurants.py
"""

import urllib.request
import urllib.parse
import json

AMAP_KEY = "290aab8bc6b28f9449e563c8cc2a6eff"
API_URL = "https://restapi.amap.com/v3/place/text"

# 待验证餐馆列表: (店名, 城市/区域, 分类标签)
RESTAURANTS = [
    # 赤水
    ("赤水第一烧",   "赤水市", "烧烤夜宵"),
    ("老双竹家常馆", "赤水市", "土菜家常"),
    ("正宗陈豆花",   "赤水市", "豆花小吃"),
    ("乡村印象",     "赤水市", "土菜家常"),
    ("食为天酒楼",   "赤水市", "综合餐厅"),
    ("四哥叉洋芋",   "赤水市", "特色小吃"),
    # 千户苗寨
    ("草堂茶居",     "雷山县", "苗族特色"),
    ("阿浓苗家",     "雷山县", "苗族特色"),
    ("苗寨人家",     "雷山县", "苗族特色"),
]

def search(name, city):
    params = urllib.parse.urlencode({
        "key":      AMAP_KEY,
        "keywords": name,
        "city":     city,
        "types":    "050000",   # 餐饮服务大类
        "output":   "json",
        "offset":   3,
    })
    req = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def main():
    print("=" * 65)
    print("  高德地图餐馆验证结果")
    print("=" * 65)

    found, not_found = [], []

    for name, city, tag in RESTAURANTS:
        try:
            data = search(name, city)
            pois = data.get("pois", [])

            if pois:
                p = pois[0]
                addr   = p.get("address", "地址未知")
                tel    = p.get("tel", "电话未知")
                rating = p.get("biz_ext", {}).get("rating", "—")
                # 精确匹配检查
                matched = name in p.get("name", "")
                mark = "✅" if matched else "⚠️ (名称相近)"
                print(f"\n{mark} 【{name}】({tag})")
                print(f"   高德店名: {p.get('name', '')}")
                print(f"   地址: {addr}")
                print(f"   电话: {tel}")
                print(f"   评分: {rating}")
                if matched:
                    found.append(name)
                else:
                    not_found.append(f"{name}(名称相近，需人工确认)")
            else:
                print(f"\n❌ 【{name}】({tag}) — 高德未找到")
                not_found.append(name)

        except Exception as e:
            print(f"\n⚠️  【{name}】查询失败: {e}")
            not_found.append(f"{name}(查询异常)")

    print("\n" + "=" * 65)
    print(f"✅ 确认存在 ({len(found)} 家): {', '.join(found)}")
    if not_found:
        print(f"❌ 未确认   ({len(not_found)} 家): {', '.join(not_found)}")
    print("=" * 65)

if __name__ == "__main__":
    main()
