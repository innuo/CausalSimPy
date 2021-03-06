import cdt
import networkx as nx
import pandas as pd
import numpy as np
from sklearn.base import TransformerMixin


class CausalStructure:
    def __init__(self, variable_names, dag=None):
        self.variable_names = variable_names
        self.dag = nx.empty_graph(len(variable_names), create_using=nx.DiGraph())
        self.dag = nx.relabel_nodes(self.dag, dict(zip(range(len(variable_names)), variable_names)))

        if dag is not None:
            self.dag = nx.compose(dag, self.dag)

        self.make_graph_properties()

    def make_graph_properties(self):
        self.topo_sorted = list(nx.topological_sort(self.dag))
        self.parents = dict(zip(self.variable_names, [[]] * len(self.variable_names)))
        self.roots = []
        self.non_roots = []
        for v in self.topo_sorted:
            parents = list(nx.DiGraph.predecessors(self.dag, v))
            self.parents[v] = parents
            if len(parents) == 0:
                self.roots.append(v)
            else:
                self.non_roots.append(v)

    # TODO: improve structure learning
    def learn_structure(self, dataset):
        gs = cdt.causality.graph.bnlearn.GS()
        
        for d in dataset.raw_datasets:
            d_copy = d.copy()
            d_copy.dropna()
            for v in d_copy: #stupid shit
                if d_copy[v].dtype.name == 'category':
                    d_copy[v] = d[v].apply(lambda x: 'v%s'%x)
                
            dataset_dag = gs.create_graph_from_data(d_copy)
        self.update_structure(dataset_dag, 'union', 'self')

    def update_structure(self, dag, merge_type='add', priority='self'):
        if merge_type == "replace":
            self.dag = dag
        else:
            self.merge(dag, merge_type, priority)
        self.make_graph_properties()

    def merge(self, dag, merge_type="union", priority="self"):
        """ merge_type = "union" is a simple compose of the two graphs with possible cycles
            merge_type = "add" adds edges from dag to self.dag,
                          any conflicts in the edges are resolved by the priority arg
        """
        if merge_type == 'union':
            self.dag = nx.compose(dag, self.dag)
            if not nx.is_directed_acyclic_graph(self.dag):
                print('Error: After merge no longer a DAG')
        elif merge_type == 'add':
            g1 = self.dag if priority == 'self' else dag
            g2 = dag if priority == 'self' else self.dag
            for e in g2.edges:
                if not g1.has_edge(e[1], e[0]):
                    g1.add_edge(e[0], e[1])
            self.dag = g1
        else:
            print('Error: merge_type' + merge_type + ' not supported')

    def plot(self):
        nx.draw_networkx(self.dag)
    pass


class DataFrameImputer(TransformerMixin):

    def __init__(self):
        """Impute missing values.

        Columns of dtype object are imputed with the most frequent value 
        in column.

        Columns of other types are imputed with mean of column.

        """
    def fit(self, X, y=None):

        self.fill = pd.Series([X[c].value_counts().index[0] if X[c].dtype == np.dtype('O') 
                                else X[c].mean() for c in X], index=X.columns)

        return self

    def transform(self, X, y=None):
        return X.fillna(self.fill)



if __name__ == '__main__':
    from datahandler import dataset as ds
    r = ds.DataSet([pd.read_csv("../data/5d.csv")])
    cs = CausalStructure(r.variable_names)
    cs.learn_structure(r)
    cs.plot()