import yake
import string

def cleant(text):
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    # # text = " ".join(text.split())
    # text = text.split()
    # for i in text:
    #     if len(i) == 1: text.remove(i)
    return text

def kwords(text):
    if text.count(' ') == 0:
        return text

    text2 = cleant(text)

    extractor = yake.KeywordExtractor(
        lan="ru",
        n=3,
        dedupLim=0.3,
        top=5,
    )

    st = extractor.extract_keywords(text2)

    # print("Ключевые фразы:")
    # for i in st:
    #     print(f"{i[0]} (сумма веса: {i[1]})")

    try:
        return st[0][0]
    except:
        return text

# text = "как скачать python 3.10"

# print(cleant(text))