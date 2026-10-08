import io
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


JPX_PAGE_URL = (
    "https://www.jpx.co.jp/"
    "markets/statistics-equities/"
    "misc/01.html"
)


def find_latest_jpx_excel():

    print("JPX PAGE: START")

    response = requests.get(
        JPX_PAGE_URL,
        timeout=60,
        headers={
            "User-Agent":
                "Mozilla/5.0 jp-stock-note-bot/1.0"
        },
    )

    if response.status_code != 200:
        raise RuntimeError(
            "JPX page download failed: "
            f"{response.status_code}"
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    candidates = []

    for link in soup.find_all("a", href=True):

        href = link["href"]

        lower = href.lower()

        if (
            lower.endswith(".xls")
            or lower.endswith(".xlsx")
        ):
            candidates.append(
                urljoin(
                    JPX_PAGE_URL,
                    href,
                )
            )

    if not candidates:
        raise RuntimeError(
            "JPX Excel link was not found"
        )

    print(
        "JPX EXCEL CANDIDATES:",
        len(candidates)
    )

    # このページの最新掲載Excelを使用
    excel_url = candidates[0]

    print(
        "JPX EXCEL:",
        excel_url
    )

    return excel_url


def collect_jpx_universe():

    print("JPX UNIVERSE: START")

    excel_url = find_latest_jpx_excel()

    response = requests.get(
        excel_url,
        timeout=60,
        headers={
            "User-Agent":
                "Mozilla/5.0 jp-stock-note-bot/1.0"
        },
    )

    if response.status_code != 200:
        raise RuntimeError(
            "JPX universe download failed: "
            f"{response.status_code}"
        )

    df = pd.read_excel(
        io.BytesIO(response.content)
    )

    print(
        "JPX RAW ROWS:",
        len(df)
    )

    print(
        "JPX COLUMNS:",
        list(df.columns)
    )

    required = [
        "コード",
        "銘柄名",
        "市場・商品区分",
    ]

    for column in required:

        if column not in df.columns:
            raise RuntimeError(
                f"JPX column missing: {column}"
            )

    # ========================================
    # Prime / Standard / Growth
    # ========================================

    market = df[
        df["市場・商品区分"]
        .astype(str)
        .str.contains(
            "プライム|スタンダード|グロース",
            regex=True,
            na=False,
        )
    ].copy()

    market["コード"] = (
        market["コード"]
        .astype(str)
        .str.strip()
    )

    market = market[
        market["コード"] != ""
    ]

    market = market.drop_duplicates(
        subset=["コード"]
    )

    stocks = []

    for _, row in market.iterrows():

        stocks.append(
            {
                "code":
                    str(row["コード"]),

                "name":
                    str(row["銘柄名"]),

                "market":
                    str(
                        row[
                            "市場・商品区分"
                        ]
                    ),
            }
        )

    print("JPX UNIVERSE: PASS")

    print(
        "TOKYO STOCKS:",
        len(stocks)
    )

    return stocks


if __name__ == "__main__":

    stocks = collect_jpx_universe()

    print("")
    print("==============================")
    print("JPX UNIVERSE TEST: SUCCESS")
    print("==============================")

    print(
        "Stocks:",
        len(stocks)
    )

    print("")

    for stock in stocks[:10]:
        print(stock)
