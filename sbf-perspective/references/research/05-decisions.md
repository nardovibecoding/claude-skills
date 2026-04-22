# Sam Bankman-Fried (SBF) — 關鍵決策分析

> Agent 調研成果 | 調研日期：2026-04-07
> 信息標注：[一手] = SBF本人解釋 | [二手] = 外部分析 | [推斷] = 歸納性分析

---

## 決策框架：理解SBF的「決策操作系統」

[推斷] SBF的每個重大決策，均可溯源到同一套邏輯：
1. **Expected Value最大化**：所有選項都折算成預期回報，選EV最高的
2. **後果主義**：結果決定行為的道德性，過程和手段不重要
3. **規模偏好**：影響越大越好，小而確定的善 < 大而不確定的善（即高風險押注合理）
4. **信任是工具**：建立信任不是道德行為，是獲得影響力的工具

這套系統在他的公開敘述中以正面語言呈現（「我只是在最大化對世界的好處」），在Vox DM中以其裸體形態呈現（「yeah just PR」）。

---

## 決策一：從Jane Street到創業（2017年）

**決策**：離開年薪百萬的Jane Street量化交易職位，創辦Alameda Research
**時間**：2017年

[二手，via research.md] MacAskill的「earn to give」模型說服SBF：高薪工作 + 捐款 = 最大社會影響。但SBF更進一步：自己創業 + 捐款更多 = 更大EV。

[推斷] 這是他第一個用EA框架「合理化」極端風險的決策——放棄安全收入追求潛在的指數級影響力。Jane Street訓練了他對概率和套利的系統性思維，他把這套工具帶入了加密市場。

**決策邏輯**：EV(創業) > EV(打工)，即使風險高很多倍

---

## 決策二：創辦Alameda Research（2017年）

**決策**：利用加密貨幣市場的跨交易所套利機會，建立量化交易公司
**核心操作**：比特幣在日本交易所比美國貴10-20%（「Kimchi Premium」類似的日本溢價），大量套利

[推斷] Alameda的原始商業模式是真實且盈利的——純量化套利，無結構性欺詐。問題不在於起點，在於後來當市場套利機會消失後，Alameda的風險胃口已被養大。

---

## 決策三：創辦FTX（2019年）

**決策**：從交易所客戶轉型為交易所創辦人
**時間**：2019年，在香港
**地點選擇**：香港→巴哈馬（2021年）——監管套利

[一手，via The Block採訪] "FTX did not have its own bank accounts [in early days]... it was hard to get bank accounts as an international cryptocurrency exchange."

[推斷] FTX從一開始就面臨結構性問題：缺乏銀行帳戶迫使客戶把資金打入Alameda的帳戶，這為後來的「資金混同」埋下了技術性基礎。SBF後來把這個銀行帳戶問題作為解釋資金流向的重要依據。

**關鍵設計問題**：FTX和Alameda帳戶在系統設計層面存在漏洞，使Alameda可以佔用FTX客戶資金，而審計系統無法有效識別。

---

## 決策四：給Alameda特殊交易權限（時間不明確）

**決策**：Alameda在FTX上獲得特殊帳戶權限，包括「延遲清算」（delayed liquidation）
**後果**：Alameda在FTX崩盤時的巨額虧損無法被正常清算，直接引發$8B缺口

[一手] "I'm not entirely sure how those decisions... became made."
[一手] "No one was really Alameda's core [decision-maker]."
[一手] "It gets to, at the very least, a dereliction of my duty."

[推斷] 這是最關鍵的結構性決策，也是最難說清的。SBF稱「以為是交易量問題而非信貸問題」——但監管機構認為這是故意設計，為Alameda提供無限信貸額度。

**決策邏輯（SBF版本）**：關心Alameda交易量佔比，未關心信貸風險敞口
**決策邏輯（檢察官版本）**：故意讓Alameda可以無限借用FTX客戶資金

---

## 決策五：1億美元政治捐款（2022年）

**決策**：成為2022年中期選舉前美國最大個人民主黨捐款人
**金額**：$100M+
**理由（公開）**：影響加密監管政策，EA框架下的最大化影響力

[推斷] 這個決策在SBF的EV框架下完全自洽：用相對小額資金影響立法 = 高EV。但它同時為FTX建立了政治護盾，讓監管機構對FTX的審查更加謹慎。兩個目標在同一個決策中被同時服務。

[推斷] 資金來源問題：$100M捐款的資金同樣可能來自客戶資金池，雖然難以直接追蹤。

---

## 決策六：11月7日發出「一切正常」推文（2022年11月）

**決策**：在已察覺FTX流動性危機的情況下，向公眾發出reassuring推文
**時間**：2022年11月7日
**後果**：推文延緩了客戶提款，客戶在資金已無法兌付時繼續留在平台

[一手] "I tweeted it with... an outlook on things that I, within a day or so, began to feel was not realistic."
[一手] "I vetoed a lot of versions of it that I thought were not true... and pared it down quite a bit."
[一手] "I don't feel great about that tweet."

[推斷] 這個決策在法律上屬於最明確的欺詐行為之一——明知問題存在，仍對公眾撒謊，且直接影響了客戶的行動。SBF的辯護是時間線混亂（「到底是第6日還是第7日察覺？」），但陪審團不接受。

---

## 決策七：不申請破產 vs 申請Chapter 11（2022年11月11日）

**決策**：在巨大壓力下申請Chapter 11破產保護
**SBF事後立場**：這是他最後悔的決定，認為不申請的話客戶本可全額取回資金

[一手] "biggest single fuckup... the one thing everyone told me to do: file for Chapter 11 bankruptcy."
[一手] "If [I] hadn't filed, withdrawals would be opening up in a month with customers fully whole."

[推斷] 這個觀點幾乎沒有得到任何外部支持——$8B的缺口不可能在一個月內填補。但這個立場對SBF很重要：它把破產申請而非資金挪用定性為「真正的錯誤」，試圖在敘事上重構事件的關鍵轉折點。

---

## 決策八：巴哈馬逮捕前不逃跑（2022年12月）

**決策**：在美方提出引渡請求前，SBF留在巴哈馬而非逃往無引渡國
**時間**：2022年12月12日被捕，12月13日同意引渡

[一手] "I presume I could [leave], but this is where I've been running FTX from for the last year."
[一手] "There still are things that need to get done."

[推斷] 是否留下是真實選擇或沒有選擇？一種解讀是他真的相信自己有辦法解決問題（EA邏輯驅動的過度自信）；另一種是計算了逃跑的EV更低（會加重罪名 + 外逃目的地有限）。

---

## 決策九：出庭作証（2023年10月審判）

**決策**：罕見地選擇出庭為自己作証
**結果**：7項罪名全部成立

[推斷] 出庭本身是一個高風險決策——大多數白領犯罪被告的律師建議不出庭。SBF選擇出庭，可能反映了他對自己說服能力的過度自信（一種在他整個創業生涯中持續存在的認知偏差）。

---

## 決策模式總結

| 決策 | 表面邏輯 | 深層邏輯 | 結果 |
|------|----------|----------|------|
| 離開Jane Street | EV最大化 | 雄心驅動 | 成就Alameda |
| FTX選址巴哈馬 | 監管友善 | 規避美國監管 | 短期成功，長期放大風險 |
| Alameda特殊權限 | 「沒有想到信貸風險」 | 為Alameda提供無限資金 | FTX崩盤核心原因 |
| 政治捐款 | 影響監管政策 | 建立政治護盾 | 崩盤後政治反彈 |
| 11月7日推文 | 安撫市場 | 爭取時間 | 詐欺定罪核心証據 |
| 後悔申請破產 | 相信可以自救 | 試圖重構敘事框架 | 無說服力 |
