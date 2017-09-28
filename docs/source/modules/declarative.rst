.. Constraints documentation master file, created by
   sphinx-quickstart on Sun Aug 27 13:35:08 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

constraints.declarative
=======================

.. automodule:: constraints.declarative
   :members:

Given the following SQL alchemy models.

.. code-block:: python

   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy import Column, Integer, String, \
       Boolean, ForeignKey, create_engine, UniqueConstraint

   from constrainst.declarative import FromModel


   class Parent(Base):
       __tablename__ = "parent"

       parent_id = Column(Integer, primary_key=True)


   class Child(Base):
       __tablename__ = "child"

       child_id = Column(Integer, primary_key=True)

       name = Column(String(10), nullable=False)
       opt = Column(Boolean)

       parent_id = Column(Integer, ForeignKey("parent.parent_id"))
       __table_args__ = (
           UniqueConstraint("parent_id", "name"),
       )

   def to_camel_case(snake_str):
       components = snake_str.split('_')
       return components[0] + "".join(x.title() for x in components[1:])

Create constraints to validate representations of the Child entity.

>>> cn = FromModel(Child, key_map=to_camel_case)
>>> obj = {"parentId": 1, "name": 11 * "x"}
>>> cn.check(obj, session=session)

.. autoclass:: constraints.declarative.FromModel
   :members:
