# Functions for performing analysis in the article
# "Third Wave Materiality: Digital Excavation of Homemade Facemask Production
# during the COVID-19 Pandemic"
#
# Code Written By: Jon Clindaniel
#
# For import/use instructions, see README.md

import pandas as pd
import geopandas as gpd
import nltk
import itertools
import collections
import seaborn as sns
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes

# download necessary NLTK Data if don't already have it
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('wordnet', quiet=True)

# Define general stop words + study-specific stop-words
stop = nltk.corpus.stopwords.words('english') \
       + ["face", "mask", "masks", "facemask", "facemasks"]

# Term lists
intentionality_eff = \
[("two", "layer"), ("double", "layer"), ("2", "layer"),
("three", "layer"), ("triple", "layer"), ("3", "layer"),
("multi", "layer"), ("multiple", "layer"), "multilayer", "multilayered",
"upf", "uv", "thick", "cotton",
("adjustable", "fit"), ("form", "fit"), ("snug", "fit"), ("tight", "fit"),
("nose", "wire"),
("cover", "chin"), ("cover", "nose"), ("cover", "mouth"),
("filter", "pocket"), "cotton", "kn95", "n95"]

intentionality_ineff = \
["mesh", "crochet", "yarn", "lace", "hole",
("one", "layer"), ("single", "layer"), ("1", "layer"),
"compliance", "antimask", ("anti", "mask"), "protest"]

unintentionality_ineff = ["valve", "thin", "loose"]

mesh = ["mesh"]

antimask = ["antimask", ("anti", "mask")]

# List of states won by Biden and Trump, respectively
biden = ["Washington", "Oregon", "California", "Nevada",
         "Arizona", "New Mexico", "Colorado", "Hawaii",
         "Minnesota", "Wisconsin", "Illinois", "Michigan",
         "Georgia", "Pennsylvania", "Virginia", "Maryland",
         "New Jersey", "New York", "Massachusetts", "Connecticut",
         "Rhode Island", "Delaware", "Vermont", "New Hampshire",
         "Maine"]

trump = ["Alaska", "Idaho", "Utah", "Montana",
         "Wyoming", "North Dakota", "South Dakota", "Nebraska",
         "Kansas", "Oklahoma", "Texas", "Iowa",
         "Missouri", "Arkansas", "Louisiana", "Indiana",
         "Kentucky", "Tennessee", "Mississippi", "Alabama",
         "West Virginia", "Ohio", "North Carolina", "South Carolina",
         "Florida"]


def process_data(data_path='data/'):
    '''
    Takes clean Etsy data (in subdirectory provided as input)
    and processes it for user. All of the necessary files (SHP file
    containing polygon boundaries of U.S. states from the U.S. Census Bureau
    as of 2020, along with a CSV of collected Etsy facemask data that has
    had its text columns pre-cleaned of extraneous characters) are
    in the data/ subdirectory of this repository, so `data/` is the default
    path.

    Returns Pandas DataFrame (with lemmatized and tokenized
    listing titles), along with a GeoPandas DataFrame, containing
    U.S. state polygons from the 2020 census (shp)
    '''
    df = pd.read_csv(data_path + 'clean_etsy_data.csv')
    df['date_collected'] = pd.to_datetime(df['date_collected'])
    df['lemmas'] = df['listing_title'].apply(get_lemmas)
    df['tokens'] = df['listing_title'].apply(get_all_tokens)

    states = gpd.read_file(data_path + 'cb_2020_us_state_20m.shp')
    return df, states


def get_wordnet_pos(word):
    '''
    Tags each word with its Part-of-speech indicator

    (Specifically used for lemmatization in the get_lemmas function)
    '''
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": nltk.corpus.wordnet.ADJ,
                "N": nltk.corpus.wordnet.NOUN,
                "V": nltk.corpus.wordnet.VERB,
                "R": nltk.corpus.wordnet.ADV}

    return tag_dict.get(tag, nltk.corpus.wordnet.NOUN)


def get_all_tokens(text):
    '''
    Tokenizes string input, including stop words
    '''
    tokens = [i for i in nltk.word_tokenize(text)]
    return tokens


def get_lemmas(text):
    '''
    Returns lemmas for a string input, excluding stop words, punctuation,
    as well as a set of study-specific stop-words
    '''
    tokens = [i for i in nltk.word_tokenize(text) if i not in stop]
    lemmas = [nltk.stem.WordNetLemmatizer().lemmatize(t, get_wordnet_pos(t))
              for t in tokens]
    return lemmas


def pct_match(terms, df, groupby, stopwords=True, exclude=[],
              plot_by_term=False, shp_df=None):
    '''
    Computes the % of products that mention at least one of the terms in the
    input term list `terms` in the DataFrame df (generated by running
    `process_data` function).

    Returns a Pandas Series of percentages (indexed by columns input in the
    `groupby` parameter)

    Users can optionally filter out stopwords by setting `stopwords` to
    True/False, exclude certain terms from the analysis by listing them as a
    list of strings for `exclude`, and visualize the distribution of each term
    across the U.S. states by providing input to the `plot_by_term` (boolean,
    where True tells the function to plot the distribution of each term)
    and `shp_df` (GeoPandas DataFrame of U.S. State polygons) parameters.
    '''
    df_copy = df[['state', 'date_collected']].copy(deep=True)

    if stopwords:
        tokens = df.lemmas
    else:
        tokens = df.tokens

    for term in terms:
        # handles both bigrams (tuples of strings) and unigrams (strings):
        if type(term) == tuple:
            df_copy.loc[:, str(term)] = \
                tokens.apply(lambda x: term in list(nltk.bigrams(x))
                or tuple([word for word in reversed(term)])
                    in list(nltk.bigrams(x)))
        else:
            df_copy.loc[:, str(term)] = \
                df.listing_title.apply(lambda x: term in x
                                       and all(item not in x
                                               for item in exclude))
        if plot_by_term:
            df_partial = df_copy[['state', 'date_collected', str(term)]
                                ].copy(deep=True)
            df_partial.loc[:, 'match'] = df_partial.loc[:, str(term)]
            pct_match = (df_partial.groupby(groupby).match.sum()
                         / df_partial.groupby(groupby).match.count()) * 100
            if groupby == 'state':
                plot_pct_by_state(pct_match, term, shp_df, scale=True)
            else:
                plot_pct_by_state_date(pct_match, term, shp_df, scale=True)

    df_copy.loc[:, 'match'] = df_copy.iloc[:,2:].any(axis=1)
    pct_match = (df_copy.groupby(groupby).match.sum()
                 / df_copy.groupby(groupby).match.count()) * 100
    return pct_match


def plot_pct_by_state(pct, terms_name,  shp_df,
                      scale=False, export_to_csv=False, save_fig=False):
    '''
    Required Input: a pandas series of percentages indexed by state (`pct`),
    a string that denotes the name of the term list being studied
    (`terms_name`), and a `geopandas` dataframe of U.S. state polygons,
    Optional Input: Whether (boolean) to scale color-bar relative to the
    maximum percentage in data (or relative to 100% -- False/default),
    whether (boolean) to export results to CSV (for further analysis)
    (`export_to_csv`), and whether (boolean) to save as a high-resolution
    figure for publication (`save_fig`)

    Output: A map indicating the percentage of products (by color) in a state
    that indicate at least one of the terms in the terms list being studied
    '''
    if scale:
        vmax = pct.max()
    else:
        vmax = 100

    fig, ax = plt.subplots(figsize=(10, 10))

    states = shp_df.merge(pct, how='left', left_on='NAME', right_on='state') \
                   .fillna(0)

    states_48 = states[~states['NAME'].isin(['Alaska',
                                             'Hawaii',
                                             'Puerto Rico'])]

    if export_to_csv:
        states[['NAME', 'match']].to_csv(terms_name + '_agg.csv')

    plot = states_48.plot(column='match',
                          cmap='viridis',
                          vmin=0,
                          vmax=vmax,
                          ax=ax) \
                    .axis('off')

    # Plot Alaska and Hawaii in the lower left corner of US Map
    axins = zoomed_inset_axes(ax, .3, loc=3, bbox_to_anchor=(0,-.05),
                              bbox_transform=ax.transAxes)
    axins2 = zoomed_inset_axes(ax, 1, loc=3, bbox_to_anchor=(.18,-.075),
                               bbox_transform=ax.transAxes)

    minx,miny,maxx,maxy =  (-178, 46, -135, 73) # Alaska
    axins.set_xlim(minx, maxx)
    axins.set_ylim(miny, maxy)

    minx,miny,maxx,maxy =  (-162, 15, -152, 25) # Hawaii
    axins2.set_xlim(minx, maxx)
    axins2.set_ylim(miny, maxy)

    # Plot zoom window
    states.loc[(states['STUSPS'] == "AK")] \
                   .plot(column='match', cmap='viridis', vmin=0, vmax=vmax,
                         ax=axins) \
                   .axis('off')
    states.loc[(states['STUSPS'] == "HI")] \
                   .plot(column='match', cmap='viridis', vmin=0, vmax=vmax,
                         ax=axins2) \
                   .axis('off')

    fig.colorbar(ax.collections[0], ax=ax, shrink=0.75,
        location='bottom', pad=0.05,
        label="Total % of Products with {} (by State)".format(terms_name))

    if save_fig:
        file_name = terms_name + '_synchronic' + '.tiff'
        fig.savefig(file_name, dpi=300, format="tiff", bbox_inches="tight",
                    pil_kwargs={"compression": "tiff_lzw"})


def plot_pct_by_state_date(pct, terms_name, shp_df,
                           scale=False, export_to_csv=False, save_fig=False):
    '''
    Required Input: a pandas series of percentages indexed by
    *state & date* (`pct`), a string that denotes the name of the term list
    being studied (`terms_name`), and a `geopandas` dataframe of U.S. state
    polygons
    Optional Input: Whether (boolean) to scale color-bar relative to the
    maximum percentage in data (or relative to 100% -- False/default),
    whether (boolean) to export results to CSV (for further analysis)
    (`export_to_csv`), and whether (boolean) to save as a high-resolution
    figure for publication (`save_fig`)

    Output: A map indicating the percentage of products (by color) in a state
    (for each of the four dates that data was collected in the study)
    that indicate at least one of the terms in the terms list being studied
    '''
    pct = pct.reset_index()
    fig, axes = plt.subplots(nrows=2,
                             ncols=2,
                             figsize=(15, 10),
                             constrained_layout=True)
    axes = axes.ravel()
    if scale:
        vmax = pct['match'].max()
    else:
        vmax = 100
    dates = ['2020-7-25', '2020-11-3', '2021-1-20', '2021-5-10']
    for i, date in enumerate(dates):
        axes[i].set_title(date, fontsize=20)
        states = shp_df.merge(pct[pct.date_collected == pd.to_datetime(date)],
                              how='left',
                              left_on='NAME',
                              right_on='state') \
                       .fillna(0)

        if export_to_csv:
            states[['NAME', 'match']].to_csv(terms_name + '_' + date + '.csv')

        states_48 = states[~states['NAME'].isin(['Alaska',
                                                 'Hawaii',
                                                 'Puerto Rico'])]
        plot = states_48.plot(column='match',
                          cmap='viridis',
                          figsize=(10,10),
                          ax=axes[i],
                          vmin=0,
                          vmax=vmax) \
                 .axis('off')

        # Plot Alaska and Hawaii in the lower left corner of US Map
        axins = zoomed_inset_axes(axes[i], .3, loc=3, bbox_to_anchor=(0,-.05),
                                  bbox_transform=axes[i].transAxes)
        axins2 = zoomed_inset_axes(axes[i], 1, loc=3,
                                   bbox_to_anchor=(.18,-.075),
                                   bbox_transform=axes[i].transAxes)

        minx,miny,maxx,maxy =  (-178, 46, -135, 73) # Alaska
        axins.set_xlim(minx, maxx)
        axins.set_ylim(miny, maxy)

        minx,miny,maxx,maxy =  (-162, 15, -152, 25) # Hawaii
        axins2.set_xlim(minx, maxx)
        axins2.set_ylim(miny, maxy)

        states.loc[(states['STUSPS'] == "AK")] \
                       .plot(column='match', cmap='viridis', vmin=0, vmax=vmax,
                             ax=axins) \
                       .axis('off')
        states.loc[(states['STUSPS'] == "HI")] \
                       .plot(column='match', cmap='viridis', vmin=0, vmax=vmax,
                             ax=axins2) \
                       .axis('off')

    cb = fig.colorbar(axes[0].collections[0], ax=axes, shrink=0.75,
        location='bottom')
    cb.set_label(label="Total % of Products with {} (by State)".format(
                                                                terms_name),
                 size=15)
    cb.ax.tick_params(labelsize=12)

    if save_fig:
        file_name = terms_name + '_diachronic' + '.tiff'
        fig.savefig(file_name, dpi=300, format="tiff", bbox_inches="tight",
                    pil_kwargs={"compression": "tiff_lzw"})


def plot_pct_by_vote(pct_biden, pct_trump, terms_name, save_fig=False):
    '''
    Input: 2 multi-index Pandas Series (pct_biden, pct_trump)
    containing data related to states that were won in the 2020
    by Biden and Trump, respectively. Each Series is indexed by (state, date)
    and contains the percentage of products at each state and date that
    contain at least one term contained within the list denoted by the
    string `terms_name`.
    Optional Input: Whether (boolean) to save as a high-resolution figure for
    publication (`save_fig`)

    Output: Plots line plots indicating the average percentage at each date for
    states that voted for each presidential candidate. 95% CIs are denoted
    around each line for statistical comparison.
    '''
    df_biden = pct_biden.reset_index()
    df_biden = df_biden.melt('date_collected', 'match',
                             value_name='percentage_match')
    sns.lineplot(data=df_biden, x='date_collected', y='percentage_match',
                 label='States Voting for Biden')

    df_trump = pct_trump.reset_index()
    df_trump = df_trump.melt('date_collected', 'match',
                             value_name='percentage_match')
    ax = sns.lineplot(data=df_trump, x='date_collected', y='percentage_match',
                      label='States Voting for Trump')
    plt.xticks(rotation=90)
    plt.xlabel('Date')
    plt.ylabel('% {}'.format(terms_name))

    if save_fig:
        file_name = terms_name + '_vote' + '.tiff'
        plt.savefig(file_name, dpi=300, format="tiff", bbox_inches="tight",
                    pil_kwargs={"compression": "tiff_lzw"})