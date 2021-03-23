import pandas as pd
import codecs
from sklearn.tree import DecisionTreeClassifier
import eli5
from eli5.lime import TextExplainer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier
import pymorphy2
import re
from bs4 import BeautifulSoup
from functools import lru_cache

def read_words(words_file):
    return [word for line in codecs.open(words_file, 'r', encoding='utf8') for word in line.split(',')]

@lru_cache(maxsize=4096)
def cache_stemmer(word):
    return re.sub('ё', 'е', morph.parse(str(word))[0].normal_form)


def ProjStemmer(wordlist):
    return [cache_stemmer(i) for i in wordlist]


def morphText(norm_text):
    return ' '.join(ProjStemmer(morphText_text.findall(
        morphText_subtext.sub(' ', morphText_suburl.sub('', BeautifulSoup(str(norm_text.lower()), 'lxml').text)))))



def get_pipe(X_train, y_train,flag_test=False, X_test=None, y_test=None):
    max_df, min_df, max_features = 0.8, 1, 200000
    stopwords = read_words('data/stopwords.txt')
    vec = TfidfVectorizer(max_df=max_df, max_features=max_features,
                          min_df=min_df, stop_words=stopwords,
                          use_idf=True, ngram_range=(1, 3))

    svd = TruncatedSVD(n_components=300, n_iter=10, random_state=seed)
    lsa = make_pipeline(vec, svd)

    clf = CatBoostClassifier(random_state=seed, loss_function='Logloss', eval_metric='TotalF1:average=Macro', logging_level='Silent')
    pipe = make_pipeline(lsa, clf)
    pipe.fit(X_train, y_train)
    if flag_test:
        print('f1 macro = {:.3f}'.format(pipe.score(X_test, y_test)))
    else:
        return pipe


def main():
    df = pd.read_excel('data/mr_vs_fr_30.xlsx')
    df = df.sample(frac=1, random_state=seed)

    df['text_lemmatized'] = df['text'].apply(morphText)

    X_train, X_test, y_train, y_test = train_test_split(
        df['text_lemmatized'], df['label'], test_size=0.3, random_state=42, stratify=df['label'])

    flag_test = True
    get_pipe(X_train, y_train, flag_test, X_test, y_test)

    flag_test = False
    pipe = get_pipe(df['text_lemmatized'], df['label'], flag_test)

    k = 0
    words = []
    for index, row in df.iterrows():
        te5 = TextExplainer(clf=DecisionTreeClassifier(max_depth=5), random_state=seed)
        te5.fit(row['text_lemmatized'], pipe.predict_proba)
        df_eli5_w = eli5.format_as_dataframe(te5.explain_weights())
        print('class {}'.format('male' if row['label'] == 0 else 'woman'))
        print('predict:')
        print(df_eli5_w)
        print(100*'*')
        temp_m = ', '.join(df_eli5_w[df_eli5_w['weight'] > 0]['feature'].tolist())
        if temp_m:
            words.append(temp_m)
        else:
            words.append('')
        k += 1

    df['words'] = words
    df.to_excel('mr_vs_fr_words_30.xlsx', index=False)


if __name__ == '__main__':
    seed=123
    morph = pymorphy2.MorphAnalyzer()
    min_word_length = 1
    max_word_length = 50
    morphText_text = re.compile('[a-zабвгдеёжзийклмнопрстуфхцчшщъыьэюяґєії]{%d,%d}' % (min_word_length, max_word_length))
    morphText_subtext = re.compile('[^a-zабвгдеёжзийклмнопрстуфхцчшщъыьэюяґєії]')
    morphText_suburl = re.compile('https?://[^\sабвгдеёжзийклмнопрстуфхцчшщъыьэюяґєії0-9]+')
    main()
