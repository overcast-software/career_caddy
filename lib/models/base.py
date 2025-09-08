from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True
    _session = None

    @classmethod
    def set_session(cls, session):
        cls._session = session

    @classmethod
    def get_session(cls):
        if cls._session is None:
            raise RuntimeError(
                "From models/base.py. Session has not been set. Call set_session() first."
            )
        return cls._session

    @classmethod
    def find_by(cls, session=None, **kwargs):
        if session is None:
            session = cls.get_session()
        try:
            return session.query(cls).filter_by(**kwargs).one_or_none()
        except NoResultFound:
            return None

    @classmethod
    def first(cls, session=None, **kwargs):
        """Retrieve the first record matching the criteria."""
        if session is None:
            session = cls.get_session()
        return session.query(cls).filter_by(**kwargs).first()

    @classmethod
    def last(cls, session=None, **kwargs):
        """Retrieve the last record (by primary key descending) matching the criteria."""
        if session is None:
            session = cls.get_session()
        query = session.query(cls).filter_by(**kwargs)
        order_cols = [col.desc() for col in cls.__mapper__.primary_key]
        return query.order_by(*order_cols).first()

    @classmethod
    def first_or_create(cls, session=None, defaults=None, **kwargs):
        if session is None:
            session = cls.get_session()
        instance = session.query(cls).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            params = {**kwargs, **(defaults or {})}
            instance = cls(**params)
            session.add(instance)
            session.commit()
            return instance, True

    @classmethod
    def first_or_initialize(cls, session=None, defaults=None, **kwargs):
        """
        Find the first instance matching the criteria or initialize a new instance.

        :param session: SQLAlchemy session to use.
        :param defaults: Default values to use for initialization if no instance is found.
        :param kwargs: Criteria to filter the query.
        :return: Tuple of (instance, boolean indicating if it was initialized).
        """
        if session is None:
            session = cls.get_session()
        instance = session.query(cls).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            params = {**kwargs, **(defaults or {})}
            instance = cls(**params)
            return instance, True

    @classmethod
    def get(cls, id, session=None):
        """Find a single record by its ID."""
        if session is None:
            session = cls.get_session()
        return session.query(cls).get(id)

    @classmethod
    def count(cls, session=None):
        """Count the number of records in the table."""
        if session is None:
            session = cls.get_session()
        return session.query(cls).count()

    def save(self):
        """Save the current instance to the database."""
        session = self.get_session()
        session.add(self)
        session.commit()

    def to_dict(self):
        """Convert the model instance to a dictionary."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
