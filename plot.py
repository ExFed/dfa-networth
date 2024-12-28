#!/usr/bin/env python3

from io import StringIO
import datetime as dt
import matplotlib.pyplot as plt
import os
import pandas as pd
import requests


def get_usa_presidents(cache_file) -> pd.DataFrame:
    if os.path.isfile(cache_file):
        return pd.read_csv(cache_file)

    query = """\
        SELECT DISTINCT ?presidentLabel ?start ?end (GROUP_CONCAT(DISTINCT ?color ; separator = ";") as ?partyColors)
        WHERE {
          ?stmt ps:P39 wd:Q11696 .
          ?president p:P39 ?stmt ;
                     wdt:P31 wd:Q5 .
          ?stmt pq:P580 ?start .
          ?stmt pq:P582 ?end .
          ?president wdt:P102 ?party .
          ?party wdt:P465 ?color .
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        }
        GROUP BY ?presidentLabel ?start ?end
        ORDER BY ?start
    """

    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "text/csv"}
    print(f"Downloading USA presidents => {cache_file}")
    response = requests.get(url, headers=headers, params={"query": query})
    response.raise_for_status()

    with open(cache_file, "w") as f:
        f.write(response.text)

    return pd.read_csv(StringIO(response.text))


def get_first_color(colors):
    return colors.split(";")[0]


def get_networth_levels(cache_file) -> pd.DataFrame:
    if os.path.isfile(cache_file):
        return pd.read_csv(cache_file)

    url = "https://www.federalreserve.gov/releases/z1/dataviz/download/dfa-networth-levels.csv"
    print(f"Downloading net worth => {cache_file}")
    response = requests.get(url)
    response.raise_for_status()

    with open(cache_file, "w") as f:
        f.write(response.text)

    return pd.read_csv(StringIO(response.text))


def parse_yearquarter(yq: str):
    y, q = yq.split(":")
    m = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}[q]
    d = 1
    return dt.datetime(int(y), m, d)


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(script_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    presidents = get_usa_presidents(os.path.join(data_dir, "usa-presidents.csv"))
    presidents["color"] = presidents["partyColors"].apply(get_first_color)

    for president in presidents.itertuples():
        name = president.presidentLabel
        start = dt.datetime.strptime(president.start, "%Y-%m-%dT%H:%M:%SZ")
        end = dt.datetime.strptime(president.end, "%Y-%m-%dT%H:%M:%SZ")
        color = president.color
        print(f"{name} ({color}) => {start} - {end}")
        plt.axvspan(start, end, alpha=0.25, color=f"#{color}")

    networth = get_networth_levels(os.path.join(data_dir, "dfa-networth-levels.csv"))

    networth["Date"] = networth["Date"].apply(parse_yearquarter)
    grouped = networth.groupby("Category")

    # Prepare data for stackplot
    dates = networth["Date"].unique()
    categories = grouped.groups.keys()
    data = {
        cat: grouped.get_group(cat).set_index("Date")["Net worth"] for cat in categories
    }

    # Ensure all categories have data for all dates
    stack_data = pd.DataFrame(data, index=dates).fillna(0).sort_index()

    # Plot stacked area plot
    plt.stackplot(stack_data.index, stack_data.T, labels=categories)
    plt.xlabel("Date")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Net worth")
    plt.yscale("log")
    plt.title("Net Worth vs Date by Wealth Percentile")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()
