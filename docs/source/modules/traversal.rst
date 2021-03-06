.. Constraints documentation master file, created by
   sphinx-quickstart on Sun Aug 27 13:35:08 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

constraints.traversal
=====================

Compute disjoint paths from a starting node to all other nodes in a digraph.

Given a digraph represented as a dict of nodes to neighbors,

.. code-block:: python

   gamma = {0: [1, 2, 6],
            1: [],
            2: [1, 4],
            3: [],
            4: [3],
            5: [1, 3],
            6: [2]}

Run `multi_paths` as follows:

>>> multi_paths(lambda i: gamma[i], 0)

.. automodule:: constraints.traversal
   :members:
