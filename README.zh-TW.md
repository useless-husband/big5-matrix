# big5-matrix

**實際量測：現今各種執行環境怎麼處理 Big5（繁體中文的傳統編碼），涵蓋每一個位元組序列和每一個相關字元。**

台灣和香港還有大量文字以 Big5 儲存和交換，而 Big5 有很多版本：微軟的 code page 950、Unicode
的 BIG5.TXT、倚天（ETEN）、Big5-2003、香港增補字符集（HKSCS）、UAO、瀏覽器用的 WHATWG 標準。
各家執行環境選了不同的版本，而且常常用同一個名字，所以一個程式用「big5」寫出的文字，另一個程式
用「big5」讀回來，可能變成別的字，而且沒有任何錯誤。本專案把 <!--n:impls.runtimes-->12<!--/n--> 種執行環境與函式庫
（Python、Go、Node.js、Rust、Java、.NET、PHP、Ruby、Perl、ICU、macOS iconv、Chromium）裡的
<!--n:impls.runs-->40<!--/n--> 個轉換器，跑過完整的一位元組與二位元組空間、以及每一個 BMP 和第二平面的字元，再跟 <!--n:impls.tables-->5<!--/n--> 份
公開的對照表比較，把所有不一致的地方都公開出來。

- **[網站](https://useless-husband.github.io/big5-matrix/docs/)**：查任何位元組序列或字元、逐類瀏覽分歧、
  任選寫入端和讀取端比較。
- **[報告](docs/divergences.md)**（英文）：家族、錯誤處理、對應爭議、來回轉換、歷史與建議。
- **[發現的問題](findings/)**：八個看起來是 bug 的問題，每個都附重現程式。
- [English](README.md) · [設計文件](docs/DESIGN.md) · [白話導讀](docs/導讀.zh-TW.md) · [資料](data/)

## 結果摘要

- Big5 核心的 <!--n:decode.hanzi_cases-->13,053<!--/n--> 個漢字，所有實作只有 <!--n:decode.hanzi_divergent-->1<!--/n--> 個不一致；其餘部分，
  <!--n:decode.nontrivial_cases-->33,024<!--/n--> 個位元組序列中有 <!--n:decode.divergent_total-->19,467<!--/n--> 個至少有兩個實作解出不同結果。
- 用一個執行環境的「big5」寫、用另一個的「big5」讀：<!--n:pair.big5.total-->110<!--/n--> 組寫讀組合中只有 <!--n:pair.big5.clean-->11<!--/n--> 組完全不掉字。
  例如 Python 把 Ё 寫成 `C7 B3`，Go 和瀏覽器讀成シ。
- `cp950` 在 Python、Perl、Ruby 是微軟的表，在 Java 和 ICU 卻是 IBM 的表。Node.js 的
  `TextDecoder('big5')` 其實是 ICU 的 windows-950，跟瀏覽器實作的 WHATWG 解碼器差了 <!--n:fact.node.vs_whatwg-->6,253<!--/n--> 個位元組序列。
- 遇到孤立的前導位元組時，<!--n:error.keep_all-->25<!--/n--> 個解碼器會保留下一個 ASCII 位元組（WHATWG 的規定），
  <!--n:error.swallow_all-->6<!--/n--> 個會把它一起吃掉，引號也不例外。Perl 會默默丟掉被截斷的最後一個字。
- macOS iconv 的 Big5 編碼器會把 <!--n:oneway.iconv.big5.to-ascii-->199<!--/n--> 個非 ASCII 字元默默換成 ASCII
  （`‹` → `<`、`„` → `"`、`∖` → `\`）；它的 BIG5-HKSCS 編碼器在 <!--n:fact.iconv.hkscs.hanzi_total-->13,053<!--/n--> 個一般漢字中有
  <!--n:fact.iconv.hkscs.hanzi_unencodable-->12,634<!--/n--> 個無法編碼。

左邊的執行環境寫入、上方的執行環境讀取，兩邊都指定「big5」（每格：默默變成別的字的數量 / 讀取端回報錯誤的數量；0 代表完全不掉字）：

<!--t:by-name-big5-->
| writer ↓ / reader → | Python | Go | Node.js | Rust | Java | .NET | PHP | Ruby | Perl | ICU | macOS iconv |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Python** | 0 | 260 / 0 | 260 / 0 | 260 / 0 | 1 / 2 | 260 / 4 | 1 / 3 | 260 / 0 | 262 / 0 | 260 / 0 | 0 |
| **Go** | 256 / 4,813 | 0 | 4,984 / 33 | 0 | 259 / 4,815 | 4,984 / 37 | 256 / 4,777 | 362 / 4,655 | 28 / 4,655 | 4,984 / 33 | 4,884 / 74 |
| **Node.js** | 259 / 4,792 | 0 | 4,970 / 33 | 0 | 262 / 4,794 | 4,970 / 33 | 259 / 4,760 | 365 / 4,638 | 32 / 4,638 | 4,970 / 33 | 4,870 / 74 |
| **Rust** | 259 / 951 | 0 | 1,129 / 33 | 0 | 262 / 953 | 1,129 / 33 | 259 / 919 | 365 / 797 | 32 / 797 | 1,129 / 33 | 1,029 / 74 |
| **Java** | 0 | 260 / 0 | 260 / 0 | 260 / 0 | 0 | 260 / 4 | 1 / 0 | 260 / 0 | 262 / 0 | 260 / 0 | 0 |
| **.NET** | 737 / 6,008 | 5,543 / 1,161 | 484 / 0 | 5,543 / 1,161 | 739 / 6,011 | 484 / 0 | 736 / 5,977 | 484 / 5,811 | 845 / 5,814 | 484 / 0 | 811 / 46 |
| **PHP** | 1 / 33 | 260 / 0 | 259 / 0 | 260 / 0 | 1 / 33 | 259 / 4 | 0 | 259 / 0 | 261 / 0 | 259 / 0 | 1 / 0 |
| **Ruby** | 260 / 193 | 366 / 43 | 0 | 366 / 43 | 263 / 195 | 0 / 4 | 259 / 165 | 0 | 361 / 3 | 0 | 334 / 44 |
| **Perl** | 264 / 194 | 35 / 40 | 363 / 0 | 35 / 40 | 267 / 196 | 361 / 2 | 261 / 164 | 363 / 0 | 0 | 363 / 0 | 271 / 41 |
| **ICU** | 260 / 6,008 | 5,059 / 1,161 | 0 | 5,059 / 1,161 | 263 / 6,010 | 0 | 259 / 5,976 | 0 / 5,811 | 361 / 5,814 | 0 | 334 / 46 |
| **macOS iconv** | 864 / 6,006 | 5,892 / 1,161 | 911 / 2 | 5,892 / 1,161 | 865 / 6,008 | 909 / 8 | 863 / 5,977 | 892 / 5,830 | 1,154 / 5,830 | 911 / 2 | 959 / 2 |
<!--/t-->

每個數字的意義請見[報告](docs/divergences.md)；本說明與報告裡的數字都是從已提交的資料產生的
（`python3 -m big5matrix report`）。

## 試試看

```
$ python3 -m big5matrix show C7 B3
decode C7 B3
  U+30B7 シ  (23)
      python.big5hkscs, go.big5, node.iconv-lite-big5, rust.big5, browser.chromium,
      java.x-ibm950, java.big5-hkscs, java.x-big5-hkscs-2001, java.x-ms950-hkscs,
      java.x-ms950-hkscs-xp, ruby.cp951, ruby.big5-hkscs, ruby.big5-uao, perl.big5-eten,
      perl.big5-hkscs, icu.ibm-950, icu.ibm-1375, icu.ibm-5471, iconv.big5-hkscs,
      iconv.big5-ibm, iconv.big5-plus, ref.whatwg, ref.hkscs-2016
  U+F760  (10)
      node.textdecoder, java.x-windows-950, dotnet.950, php.cp950, ruby.big5, ruby.cp950,
      perl.cp950, icu.windows-950-2000, icu.ibm-1373, ref.ms-bestfit950
  U+0401 Ё  (8)
      python.big5, python.cp950, java.big5, java.x-big5-solaris, php.big-5, iconv.big5,
      iconv.big5-2003, ref.unicode-big5
  error  (2)
      iconv.cp950, ref.ms-cp950
  error error  (1)
      node.iconv-lite-cp950
```

`show` 可以接位元組（`A145`）、字元（`兀`）或碼位（`U+2027`）。資料都在儲存庫裡，所以只需要
Python 3.9 以上，不需要其他執行環境。

## 運作方式

```
 cases.py：所有 1 與 2 位元組序列（65,792 個）、所有 BMP 與第二平面碼位（129,028 個）
      │
      ├──► adapters/<執行環境>/   每個執行環境一支小程式，從 stdin 讀測試案例、
      │                          用同一種行格式輸出結果；由框架負責編譯與執行
      │
      ├──► reference.py          WHATWG 演算法與索引、BIG5.TXT、CP950.TXT、bestfit950、
      │                          HKSCS-2016（公開對照表，以 SHA-256 固定版本）
      ▼
 data/decode/<實作>.txt.gz、data/encode/<實作>.txt.gz、data/manifest.json（版本、雜湊）
      │
      ├──► analyze.py ──► report/summary.json ──► docs/divergences.md、README（產生的數字）
      ├──► docs/ 網站（直接讀 data/ 與摘要，不另存一份）
      └──► check：重跑本機有的轉換器並比對（CI）
```

- **所有執行環境用同一個協定。** 轉接程式收到 `d<TAB>A140` 或 `e<TAB>00CA 0304`，回答它產生的
  碼位或位元組。解碼用該環境的「取代模式」，所以資料能看出一個錯誤吃掉幾個位元組；編碼用嚴格模式，
  所以看得到真正的對應。每個案例都從全新的轉換器狀態開始。各環境的呼叫方式見
  [`adapters/README.md`](adapters/README.md)。
- **版本鍵。** 每個轉接程式回報決定其行為的版本（Go 是 x/text 模組版本、Rust 是 crate 版本、ICU 是
  ICU 版本）。CI 的漂移檢查會重跑執行器上有的轉接程式：版本鍵相同時結果必須完全一致；版本較新時
  差異只會被回報，不算失敗。
- **精簡、可驗證的資料。** 每行一個結果、固定的案例順序、可重現的 gzip：<!--n:impls.runs-->40<!--/n--> 個轉換器加
  <!--n:impls.tables-->5<!--/n--> 份表共 5.6 MB，每個檔案都小於 100 KB。每個檔案註明它對應的案例清單，manifest 記錄它的 SHA-256。
- **第二意見。** WHATWG 欄是把規格逐步轉寫的實作；它和 encoding_rs 在全部 <!--n:decode.cases-->65,792<!--/n--> 個解碼案例
  一致，和 Chromium 只差 <!--n:fact.chromium.differs-->4<!--/n--> 個（Chromium 的 bug）。`tools/verify_claims.py` 會直接詢問各執行環境
  （用它的命令列工具或幾行獨立程式碼），再次確認每個出人意料的結論。

## 執行

需求：Python 3.9 以上（只用標準函式庫）。其他執行環境都是選配，沒有安裝的會被略過並顯示說明。

```sh
make build     # 編譯本機有執行環境的轉接程式，列出版本
make run       # 跑過所有案例並更新 data/            （下列機器上 12.9 秒）
make analyze   # 計算 report/summary.json              （43.9 秒）
make report    # 更新文件裡產生的數字
make check     # 漂移檢查：重跑並與已提交的資料比對
make test      # 單元與整合測試
make verify    # 用第二種方法確認報告中的結論
make lint      # 儲存庫裡每種語言的檢查
make serve     # 在 127.0.0.1 啟動網站（會印出網址）
```

資料是在 macOS 27.0、Apple M5（10 核、16 GB）上收集的，這台機器同時有其他工作在跑；`make run`
同時跑四個轉接程式，重跑一次得到的檔案和已提交的完全相同。測試的版本：CPython 3.13.0、Go 1.27.1 與
x/text v0.42.0、Node 25.5.0 與 iconv-lite 0.7.3、Rust 1.98.1 與 encoding_rs 0.8.42、Chromium 153
（透過 playwright-core）、OpenJDK 27、.NET 10.0.12、PHP 8.5.11、Ruby 2.6.10 與 Perl 5.34.1（macOS
內建版本）、ICU 78.3，以及 macOS 的 iconv。完整的轉換器清單見[報告](docs/divergences.md#2-what-was-tested)。

## 限制

- 沒有實際在 Windows 上執行；以微軟公開的 bestfit950 對照表代替，並標示為「表」。.NET 的 code page
  950 是唯一實際執行的微軟轉換器。
- 產生資料的機器上沒有 glibc iconv 和 GNU libiconv（多數 Linux 程式使用的轉換器）。在 Linux 上 iconv
  轉接程式會被略過，而不是拿去跟 macOS 的資料比。
- Ruby 和 Perl 是 macOS 內建的舊版本。沒有執行 Firefox 和 Safari（encoding_rs 就是 Firefox 的函式庫）。
- 案例長度只有一或兩個位元組；更長的輸入只由「前面接一個 ASCII 位元組不會改變結果」這項檢查涵蓋。
- .NET 的 code page 20002（「x-Chinese-Eten」）不是 Big5 的排列，因此不列入；PHP 的 `iconv()` 就是
  系統的 iconv，不另外列出。

## 相關研究

以前就有人比較過 Big5 的對照表，本專案建立在這些成果上：

- Bruno Haible 的[對照表比較](https://www.haible.de/bruno/charsets/conversion-tables/Big5.html)（最後更新
  2020 年 1 月）說明 libiconv、glibc、多個 JDK、ICU、Windows 等的 Big5 表彼此有哪些不同。
- HarJIT 的 [CNS 與 Big5 對照圖](https://harjit.moe/cns-conc.html)與
  [ecma35lib](https://github.com/harjitmoe/ecma35lib) 專案詳細比較各種 Big5 版本的對照表；比較的是表，
  不是實際執行的轉換器。
- MozTW 的 [Big5 頁面](https://moztw.org/docs/big5/)以表格記錄各版本（Big5-2003、UAO、HKSCS、WHATWG 標準）。
- ICU 的 [icu-data](https://github.com/unicode-org/icu-data) 保存了從許多系統收集來的廠商對照檔，大多
  來自 2000 年前後。
- WHATWG 編碼標準的 Big5 定義來自瀏覽器實測，見 Anne van Kesteren 的
  [2012 年筆記](https://annevankesteren.nl/2012/04/big5)與
  [whatwg/encoding#75](https://github.com/whatwg/encoding/issues/75)。
- 資安方面：WHATWG [issue #171](https://github.com/whatwg/encoding/issues/171) 討論無效前導位元組後面的
  ASCII，DEVCORE 的 [WorstFit](https://devco.re/blog/2025/01/09/worstfit-unveiling-hidden-transformers-in-windows-ansi/)
  研究 Windows 的 best-fit 轉換。

就我所知，本專案新增的是「實際執行現今的轉換器」而不是比較對照表：把每個位元組序列和每個相關字元
送進各執行環境的解碼器與編碼器，記錄錯誤處理方式、同一環境內與不同環境之間的來回轉換，並用檢查
追蹤這些結果隨執行環境更新而產生的變化。

## 授權

[MIT](LICENSE)。[`reference/`](reference/) 裡的對照表是第三方資料，各自有其授權條款，見
[`reference/SOURCES.md`](reference/SOURCES.md)。
