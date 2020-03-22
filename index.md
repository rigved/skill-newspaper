# $ Description
* [Mycroft AI](https://mycroft.ai/) skill to read out summaries of web pages.

# $ Author
* @rigved

# $ Parts
* [Main skill](https://github.com/rigved/webpage-summarizer-skill):
    * Mycroft AI skill to interact with the user.
    * Skill manages summarization micro-service, including its security.
    * Provides API token for remote applications to interact with the
      micro-service.
* [Web Page Summarization micro-service](https://github.com/rigved/webpage-summarizer-skill/tree/master/apiv1):
    * Secure summarization micro-service within skill.
    * Provides RESTful APIs to interact with the micro-service.
    * Provides a meta-library to generate a summary of the given web page using extractive summarization techniques.

# $ Technologies used
* [Python](https://www.python.org/)
* [Django web framework](https://www.djangoproject.com/)
* [Daphne application server](https://github.com/django/daphne)
* [Django Rest Framework](https://www.django-rest-framework.org/)
* [Mechanical Soup](https://mechanicalsoup.readthedocs.io/)
* [Gensim](https://radimrehurek.com/gensim/)
* [Mycroft AI Mark 1](https://mycroft-ai.gitbook.io/docs/using-mycroft-ai/get-mycroft/mark-1)

# $ Other Data Science related work
* [Udemy Data Science Course](https://rigved.github.io/udemy-data-science-course/)
* [Udacity Machine Learning Nanodegree](https://rigved.github.io/udacity-machine-learning/)
