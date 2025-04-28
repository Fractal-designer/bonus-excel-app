import pandas as pd
import re
import streamlit as st

# === Функция правильного парсинга строки ===
def careful_parse_row(description, currency):
    try:
        description = re.sub(r'\s+', ' ', description)
        deposit_patterns = {
            'RUB': r'на депозит от.*?([\d\s]+) RUB',
            'KZT': r'на депозит от.*?([\d\s]+) KZT',
            'AZN': r'на депозит от.*?([\d\s]+) AZN',
            'TRY': r'на депозит от.*?([\d\s]+) TRY',
            'MXN': r'на депозит от.*?([\d\s]+) MXN'
        }

        # Парсим депозит
        dep_match = re.search(deposit_patterns.get(currency, ""), description)
        dep = dep_match.group(1).replace(' ', '') + f" {currency}" if dep_match else None

        # Парсим ставку
        bet = None
        if 'по' in description:
            after_po = description.split('по', 1)[-1]
            after_po = re.split(r'в слоте|слоте', after_po)[0]  # Обрезаем по ключевым словам
            parts = [p.strip() for p in after_po.split('/')]
            for part in parts:
                if currency in part:
                    bet = part.strip()
                    break

        # Парсим фриспины
        fs_pattern = r'(\d+\sFS\s\(х\d+\))'
        fs_match = re.search(fs_pattern, description)
        fs_info = fs_match.group(1) if fs_match else None

        if dep and bet and fs_info:
            return pd.Series([dep, bet, fs_info, None])
        else:
            return pd.Series([None, None, None, description])

    except Exception as e:
        return pd.Series([None, None, None, description])

# === Интерфейс Streamlit ===
st.title("🎁 Бонус-обработчик Excel файлов")

uploaded_file = st.file_uploader("Загрузите ваш Excel-файл (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)

        # 🛠 Автокоррекция названий столбцов
        df.columns = df.columns.str.strip().str.title()  # Привести к красивому виду
        rename_dict = {
            'User Id': 'User ID',
            'Userid': 'User ID',
            'Currency': 'Currency',
            'Description': 'Description'
        }
        df.rename(columns=rename_dict, inplace=True)

        # 🧹 Оставляем только нужные столбцы
        necessary_columns = ['User ID', 'Currency', 'Description']
        df = df[[col for col in necessary_columns if col in df.columns]]

        # Проверка на наличие всех обязательных столбцов
        if not {'User ID', 'Currency', 'Description'}.issubset(df.columns):
            st.error("❌ Файл должен содержать столбцы: User ID, Currency, Description")
        else:
            # Парсинг данных
            df[['customer_dep', 'customer_stavka', 'customer_spin', 'Original Text']] = df.apply(
                lambda row: careful_parse_row(row['Description'], row['Currency']), axis=1
            )

            result_df = df[['User ID', 'Currency', 'customer_dep', 'customer_stavka', 'customer_spin', 'Original Text']]

            st.success("✅ Файл успешно обработан!")

            # Предпросмотр таблицы
            st.subheader("🔍 Предпросмотр обработанного файла")
            st.dataframe(result_df)

            # Скачать готовый файл
            st.download_button(
                label="📥 Скачать обработанный файл",
                data=result_df.to_excel(index=False, engine='openpyxl'),
                file_name="output.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Произошла ошибка обработки: {e}")
