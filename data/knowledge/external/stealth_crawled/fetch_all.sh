#!/bin/bash
# Save all successfully fetched pages
URLS=(
  "https://help.jd.com/qxhelp/question-202.html"
  "https://in.m.jd.com/help/app/tuihuanzhengce.html"
  "https://www.tmall.com/wow/seller/act/seven-day"
  "https://bk.taobao.com/k/tianmao_13/425032ffb77c3e3d18f2f45d20163be2.html"
  "https://www.cainiao-globalshipping.com/blogs/cross-border-logistics/jin-yun-qing-dan"
  "https://www.lifrog.com/38112.html"
  "https://mall.bilibili.com/taxdetail.html"
  "https://www.amz123.com/ask/2CpRKVT8"
  "https://www.woshipm.com/pd/1597533.html"
  "https://www.eservicesgroup.com.cn/news/32505.html"
  "https://m.maijiaw.com/article/622134"
  "https://help.pinduoduo.com/home/customer/"
  "https://www.2006w.com/article/2513"
  "http://www.lawyers.org.cn/info/77b49d6e13bd40b1b31202defbeb312e"
  "https://www.by56.com/news/47623.html"
  "https://blog.51tracking.com/1519-2/"
  "https://cloud.tencent.com/developer/news/1073634"
  "https://www.huichenglawyer.com/pufaku/27510.html"
  "https://news.cctv.cn/2025/04/18/ARTIm6tJAQaxM1rjb0tlQS5X250418.shtml"
)

for url in "${URLS[@]}"; do
  fname=$(echo "$url" | md5sum | cut -d' ' -f1).txt
  echo "Fetching: $url -> $fname"
  python3 ~/scripts/stealth_fetch.py "$url" --engine auto > "$fname" 2>&1
done
echo "DONE"
