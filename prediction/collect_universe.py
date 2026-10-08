import io
import requests
import pandas as pd


JPX_LIST_URL = (
    "https://www.jpx.co.jp/"
    "markets/statistics-equities/"
    "misc/tvdivq0000001vg2-att/data_j.xls"
)


def collect_jpx_universe():

    print("JPX UNIVERSE: START")

    response = requests.get(
        JPX_LIST_URL,
        timeout=60,
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

    # JPXの列名変更に備えて確認
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

    # ---------------------------------------
    # 東証普通株
    # ---------------------------------------

    market = df[
        df["市場・商品区分"].astype(str).str.contains(
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

        stocks.append({
            "code":
                str(row["コード"]),

            "name":
                str(row["銘柄名"]),

            "market":
                str(row["市場・商品区分"]),
        })

    print(
        "JPX UNIVERSE: PASS"
    )

    print(
        "TOKYO STOCKS:",
        len(stocks)
    )

    return stocks
