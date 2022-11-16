import json
import requests
from bs4 import BeautifulSoup
import argparse
import pandas as pd
from datetime import datetime
import config


"""
pipenv run python3 src/job.py -u="https://mawaqit.net/fr/grande-mosquee-de-paris" -f="./data/output/prayers.json"
pipenv run python3 airflow/dags/salat_times_ingestion.py --year="2022"
"""


def _import_data():
    url = config.SALAT_TIMES_API
    page = requests.get(url)
    soup = BeautifulSoup(page.text, "html.parser")
    item = soup.find_all("script")
    item = str(item[0])
    item = item.split("var")
    item = item[8].split("\n")[0].split(";")[0].strip().split("confData = ")
    file = open(config.JSON_FILE_DIR, "w")
    file.write(item[1])
    file.close()


def _transform_data(year):
    data_json = json.load(open(config.JSON_FILE_DIR))
    output_info_times_prayers = _get_info_times_prayers_by_day(data_json, year)
    output_iqama_times_prayers = _get_iqama_times_prayers_by_day(data_json, year)
    df_info_times_prayers = pd.DataFrame(output_info_times_prayers).set_index(['day']).apply(pd.Series.explode).reset_index()
    df_iqama_times_prayers = pd.DataFrame(output_iqama_times_prayers).set_index(['day']).apply(pd.Series.explode).reset_index()
    df_salat_times_enriched = pd.merge(df_info_times_prayers, df_iqama_times_prayers, on=["day", "name_prayers"])
    df_salat_times_enriched["time_jumua_1"] = data_json["jumua"]
    df_salat_times_enriched["time_jumua_2"] = data_json["jumua2"]
    return df_salat_times_enriched


def _get_info_times_prayers_by_day(data, year: int):
    prayers_info = []
    for month, month_values in enumerate(data["calendar"], 1):
        for day, time in month_values.items():
            try:
                prayers_info.append({'day': datetime(year, month, int(day)), 'name_prayers': ['Fajr', 'Shuruq', 'Dhouhr', 'Asr', 'Maghrib', 'Isha'], 'times_prayer': time})
            except:  # ignore 29 febuary if it's not a bisextile year
                pass
    return prayers_info


def _get_iqama_times_prayers_by_day(data, year: int):
    iqama_info = []
    for month, month_values in enumerate(data["iqamaCalendar"], 1):
        for day, iqamas in month_values.items():
            try:
                iqamas_times = [int(iqama.replace('+', '')) for iqama in iqamas]
                add_shuruq_iqama = iqamas_times[:] # we don't have iqama time for shuruq prayers, by default it's 0
                add_shuruq_iqama.insert(1, 0)
                iqama_info.append({'day': datetime(year, month, int(day)), 'name_prayers': ['Fajr', 'Shuruq', 'Dhouhr', 'Asr', 'Maghrib', 'Isha'], 'iqama_difference': add_shuruq_iqama})
            except: # ignore 29 febuary if it's not a bisextile year
                pass
    return iqama_info


def _save_df_to_csv(df):
    df.to_csv(config.CSV_FILE_DIR, index=False)


def main(year):
    _import_data()
    df = _transform_data(year)
    _save_df_to_csv(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int)
    args = parser.parse_args()
    main(args.year)