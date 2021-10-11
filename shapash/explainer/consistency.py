import itertools
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
from sklearn.manifold import MDS
plt.style.use("seaborn")

def consistency_plot(contributions=None, methods=["shap", "acv"], selection=None):
    """Consitency plot to compare contributions from multiple methods

    Parameters
    ----------
    contributions : dictionary, optional
        If provided, dictionary where key is method name and value is a DataFrame containing the contributions for a specific method, by default None
    methods : list, optional
        When contributions is None, list of methods to use to calculate contributions, by default ["shap", "acv"]
    selection: list
        Contains list of index, subset of the input DataFrame that we use for the compute of consitency statistics, by default None

    """    
    if contributions:

        methods = list(contributions.keys())
        weights = list(contributions.values())

    else: #TODO calculer les contributions définies dans l'argument "methods"
        pass

    if not all(isinstance(x, pd.DataFrame) for x in weights):
        raise ValueError('Contributions must be pandas DataFrames')
    if not all(x.shape == weights[0].shape for x in weights):
        raise ValueError('Contributions must be of same shape')

    weights = [weight.values for weight in weights]

    # Sampling
    if selection is None:
        pass
    elif isinstance(selection, list):
        if len(selection) == 1:
            raise ValueError('Selection must include multiple points')
        else:
            weights = [weight[selection] for weight in weights]
    else:
        raise ValueError('Parameter selection must be a list')

    all_comparisons, mean_distances = calculate_all_distances(methods, weights)
    method_1, method_2, l2 = find_examples(mean_distances, all_comparisons, weights)

    plot_comparison(mean_distances)
    plot_examples(method_1, method_2, l2)

def calculate_all_distances(methods, weights):
    """For each instance, calculate contributions from differents methods and measure a distance. In addition, calculate the mean distance between each pair of method

    Parameters
    ----------
    methods : list
        List of methods used in the calculation of contributions
    weights : list
        List of contributions from different methods

    Returns
    -------
    all_comparisons : array
        Array containing, for each instance and each pair of methods, the distance between the contribtuions
    mean_distances : DataFrame
        DataFrame storing all pairwise distances between methods
    """
    mean_distances = pd.DataFrame(np.zeros((len(methods), len(methods))), columns=methods, index=methods)
    
    # Initialize a (n choose 2)x4 array (n=num of instances)
    # that will contain : indices of methods that are compared, index of instance, L2 value of instance
    all_comparisons = np.array([np.repeat(None, 4)])

    for index_i, index_j in itertools.combinations(range(len(methods)), 2):
        l2_dist, pairwise_comparison = calculate_pairwise_distances(weights, index_i, index_j)
        calculate_mean_distances(methods, mean_distances, index_i, index_j, l2_dist)
        all_comparisons = np.concatenate((all_comparisons, pairwise_comparison), axis=0)

    all_comparisons = all_comparisons[1:, :]

    return all_comparisons, mean_distances

def calculate_pairwise_distances(weights, index_i, index_j):
    """For a specific pair of methods, calculate the distance between the contributions for all instances. 

    Parameters
    ----------
    weights : list
        List of contributions from 2 selected methods
    index_i : int
        Index of method 1
    index_j : int
        Index of method 2

    Returns
    -------
    l2_dist : array
        Distance between the two selected methods for all instances
    pairwise_comparison : array
        Formalisation of the l2_dist used in a later step
    """    
    # Normalize weights using L2 norm
    norm_weights_i = weights[index_i] / np.linalg.norm(weights[index_i], ord=2, axis=1)[:, np.newaxis]
    norm_weights_j = weights[index_j] / np.linalg.norm(weights[index_j], ord=2, axis=1)[:, np.newaxis]
    # And then take the L2 norm of the difference as a metric
    l2_dist = np.linalg.norm(norm_weights_i -  norm_weights_j, ord=2, axis=1)
    # Populate the (n choose 2)x4 array
    pairwise_comparison = np.column_stack(
        (np.repeat(index_i, len(l2_dist)), np.repeat(index_j, len(l2_dist)), np.arange(len(l2_dist)), l2_dist,)
    )

    return l2_dist, pairwise_comparison

def calculate_mean_distances(methods, mean_distances, index_i, index_j, l2_dist):
    """Given the contributions of all instances for two selected instances, calculate the distance between them

    Parameters
    ----------
    methods : list
        List of methods used in the calculation of contributions
    mean_distances : DataFrame
        DataFrame storing all pairwise distances between methods
    index_i : int
        Index of method 1
    index_j : int
        Index of method 2
    l2_dist : array
        Distance between the two selected methods for all instances
    """
    # Calculate mean distance between the two methods and update the matrix
    mean_distances.loc[methods[index_i], methods[index_j]] = np.mean(l2_dist)
    mean_distances.loc[methods[index_j], methods[index_i]] = np.mean(l2_dist)

def find_examples(mean_distances, all_comparisons, weights):
    """To illustrate the meaning of distances between methods, extract 5 real examples from the dataset

    Parameters
    ----------
    mean_distances : DataFrame
        DataFrame storing all pairwise distances between methods
    all_comparisons : array
        Array containing, for each instance and each pair of methods, the distance between the contribtuions
    weights : list
        List of contributions from 2 selected methods

    Returns
    -------
    method_1 : list
        Contributions of 5 instances selected to display in the second plot for method 1
    method_2 : list
        Contributions of 5 instances selected to display in the second plot for method 2
    l2 : list
        Distance between method_1 and method_2 for the 5 instances
    """    
    method_1 = []
    method_2 = []
    l2 = []

    # Evenly split the scale of L2 distances (from min to max excluding 0)
    for i in np.linspace(start=mean_distances[mean_distances>0].min().min(), stop=mean_distances.max().max(), num=5):
        # For each split, find the closest existing L2 distance
        closest_l2 = all_comparisons[:, -1][np.abs(all_comparisons[:, -1] - i).argmin()]
        # Return the row that contains this L2 distance
        row = all_comparisons[all_comparisons[:, -1] == closest_l2]
        # Extract corresponding SHAP Values
        contrib_1 = weights[int(row[0, 0])][int(row[0, 2])]
        contrib_2 = weights[int(row[0, 1])][int(row[0, 2])]
        # Prevent from displaying duplicate examples
        if closest_l2 in l2:
            continue
        method_1.append(contrib_1 / np.linalg.norm(contrib_1, ord=2))
        method_2.append(contrib_2 / np.linalg.norm(contrib_2, ord=2))
        l2.append(closest_l2)

    return method_1, method_2, l2

def calculate_coords(mean_distances):
    """Calculate 2D coords to position the different methods in the main graph

    Parameters
    ----------
    mean_distances : DataFrame
        DataFrame storing all pairwise distances between methods

    Returns
    -------
    Coordinates of each method
    """    
    return MDS(n_components=2, dissimilarity="precomputed", random_state=0).fit_transform(mean_distances)

def plot_comparison(mean_distances):
    """Plot the main graph displaying distances between methods

    Parameters
    ----------
    mean_distances : DataFrame
        DataFrame storing all pairwise distances between methods
    """    
    font = {"fontname":"Arial", "fontsize": 18, "color":'#{:02x}{:02x}{:02x}'.format(50, 50 , 50)}

    fig = plt.figure(figsize=(10, 6))
    plt.suptitle(
        "Explanation methods consistency:How similar are explanations from different methods?",
        y=1.05,
        **font
    )

    plt.title(
        "Average distances between the explanations provided\nby SHAP, LIME and Tree Interpreter", fontsize=14,
    )

    coords = calculate_coords(mean_distances)

    plt.scatter(coords[:, 0], coords[:, 1], marker="o")

    for i in range(len(mean_distances.columns)):
        plt.annotate(
            mean_distances.columns[i],
            xy=coords[i, :],
            xytext=(-5, 5),
            textcoords="offset points",
            ha="right",
            va="bottom",
        )
        draw_arrow(
            coords[i, :],
            coords[(i + 1) % mean_distances.shape[0], :],
            mean_distances.iloc[i, (i + 1) % mean_distances.shape[0]],
        )

    lim = (coords.min().min(), coords.max().max())
    margin = 0.1 * (lim[1] - lim[0])
    lim = (lim[0] - margin, lim[1] + margin)
    plt.axes().set(xlim=lim, ylim=lim)
    plt.axes().set_aspect("equal", anchor="W")
    plt.axes().set_xticklabels([])
    plt.axes().set_yticklabels([])
    plt.axes().set_xticks(plt.axes().get_yticks())

    plt.show()


def draw_arrow(a, b, dst):
    """Add an arrow in the main graph between the methods

    Parameters
    ----------
    a : array
        Coordinates of method 1
    b : array
        Coordinates of method 2
    dst : float
        Distance between the methods
    """    
    plt.annotate(
        s="",
        xy=a - 0.05 * (a - b),
        xycoords="data",
        xytext=b + 0.05 * (a - b),
        textcoords="data",
        arrowprops=dict(arrowstyle="<->"),
    )
    plt.annotate(
        s="%.2f" % dst,
        xy=(0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])),
        xycoords="data",
        textcoords="data",
        ha="center",
    )

def plot_examples(method_1, method_2, l2):
    """Plot the second graph that explains distances via the use of real exmaples extracted from the dataset

    Parameters
    ----------
    method_1 : list
        Contributions of 5 instances selected to display in the second plot for method 1
    method_2 : list
        Contributions of 5 instances selected to display in the second plot for method 2
    l2 : list
        Distance between method_1 and method_2 for the 5 instances
    """    
    y = np.arange(method_1[0].shape[0])
    fig, axes = plt.subplots(ncols=len(l2), figsize=(3*len(l2), 4))
    if len(l2) == 1: axes = np.array([axes])
    fig.suptitle("Examples of weights comparisons for various distances (L2 norm)")

    for n, (i, j, k) in enumerate(zip(method_1, method_2, l2)):
        """ # To keep a subset of features, remove the ones where abs(SHAP) according to method_1 is small
        idx = np.flip(np.abs(i).argsort())
        # Only keep the top n (according to i)
        top_n_features = 30
        idx, y = idx[-top_n_features:], y[-top_n_features:]
        _, i, j = [np.take(x, idx) for x in [self.columns, i, j]] """
        # Sort by method_1 (no abs)
        idx = np.flip(i.argsort())
        i, j = i[idx], j[idx]

        axes[n].barh(y, i, label='method 1', left=0)
        axes[n].barh(y, j, label='method 2', left=np.abs(np.max(i)) + np.abs(np.min(j)) + np.max(i)/3) # /3 to add space

        axes[n].set(xticks=[])
        axes[n].set(yticks=[])
        axes[n].set(title="$d_{L2}$ = " + str(round(k, 2)))
        axes[n].set_xlabel("Shap values")

    fig.show()