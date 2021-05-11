from datetime import datetime, timedelta

from akismet import Akismet
from django.test import RequestFactory
from django.test import TestCase
from django.utils.timezone import now
from fluent_comments import appsettings
from fluent_comments.moderation import FluentCommentsModerator, get_model_moderator
from unittest.mock import patch

from article.models import Article
from article.tests import factories
from fluent_comments.tests.utils import MockedResponse, override_appsettings

try:
    from django.urls import reverse
except ImportError:  # Django<2.0
    from django.core.urlresolvers import reverse


class ModerationTests(TestCase):
    """
    Testing moderation utils
    """

    def test_get_model_moderator(self, *mocks):
        """
        See if the moderator was registered.
        """
        moderator = get_model_moderator(Article)
        self.assertIsNotNone(moderator)

    @override_appsettings(
        FLUENT_CONTENTS_USE_AKISMET=False,
        FLUENT_COMMENTS_MODERATE_BAD_WORDS=('viagra',)
    )
    def test_bad_words(self, *mocks):
        """
        Test moderation on bad words.
        """
        request = RequestFactory().post(reverse('comments-post-comment-ajax'))
        article = factories.create_article()
        comment = factories.create_comment(article=article, comment='Testing:viagra!!')
        moderator = get_model_moderator(Article)  # type: FluentCommentsModerator

        self.assertTrue(moderator.moderate_bad_words)  # see that settings are correctly patched
        self.assertTrue(moderator.moderate(comment, article, request), "bad_words should reject")

        comment.comment = "Just normal words"
        self.assertFalse(moderator.moderate(comment, article, request), "bad_words should not trigger")

    @override_appsettings(
        FLUENT_CONTENTS_USE_AKISMET=False,
    )
    def test_moderator_no_akismet(self, *mocks):
        """
        Testing moderation without akismet
        """
        request = RequestFactory().post(reverse('comments-post-comment-ajax'))
        article = factories.create_article()
        comment = factories.create_comment(article=article)
        moderator = get_model_moderator(Article)  # type: FluentCommentsModerator

        self.assertTrue(article.enable_comments)
        self.assertFalse(moderator.akismet_check)
        self.assertTrue(moderator.allow(comment, article, request), "no akismet, comment should be allowed")
        self.assertFalse(moderator.moderate(comment, article, request), "no akismet, comment should not be moderated")

    @override_appsettings(
        AKISMET_API_KEY='FOOBAR',
        FLUENT_COMMENTS_AKISMET_ACTION='auto',
        FLUENT_CONTENTS_USE_AKISMET=True,
    )
    def test_akismet_auto(self, *mocks):
        """
        Test an akismet call
        """
        request = RequestFactory().post(reverse('comments-post-comment-ajax'))
        article = factories.create_article()
        comment = factories.create_comment(article=article, user_name='viagra-test-123')
        moderator = get_model_moderator(Article)  # type: FluentCommentsModerator

        self.assertTrue(article.enable_comments)
        self.assertTrue(moderator.akismet_check)  # see that settings are correctly patched

        with patch.object(Akismet, '_request', return_value=MockedResponse(True, definitive=True)):
            self.assertFalse(moderator.allow(comment, article, request), "akismet should reject")
            self.assertTrue(moderator.moderate(comment, article, request), "akismet should reject")
            self.assertTrue(comment.is_removed)

    @override_appsettings(
        AKISMET_API_KEY='FOOBAR',
        FLUENT_COMMENTS_AKISMET_ACTION='moderate',
        FLUENT_CONTENTS_USE_AKISMET=True,
    )
    def test_akismet_moderate(self, *mocks):
        """
        Test an akismet call
        """
        request = RequestFactory().post(reverse('comments-post-comment-ajax'))
        article = factories.create_article()
        comment = factories.create_comment(article=article, user_name='viagra-test-123')
        moderator = get_model_moderator(Article)  # type: FluentCommentsModerator

        self.assertTrue(article.enable_comments)
        self.assertTrue(moderator.akismet_check)  # see that settings are correctly patched

        with patch.object(Akismet, '_request', return_value=MockedResponse(True)):
            self.assertTrue(moderator.allow(comment, article, request))
            self.assertTrue(moderator.moderate(comment, article, request), "akismet should reject")
            self.assertFalse(comment.is_removed)

    @override_appsettings(
        AKISMET_API_KEY='FOOBAR',
        FLUENT_COMMENTS_AKISMET_ACTION='soft_delete',
        FLUENT_CONTENTS_USE_AKISMET=True,
    )
    def test_akismet_soft_delete(self, *mocks):
        """
        Test an akismet call
        """
        request = RequestFactory().post(reverse('comments-post-comment-ajax'))
        article = factories.create_article()
        comment = factories.create_comment(article=article, user_name='viagra-test-123')
        moderator = get_model_moderator(Article)  # type: FluentCommentsModerator

        self.assertTrue(article.enable_comments)
        self.assertTrue(moderator.akismet_check)  # see that settings are correctly patched

        with patch.object(Akismet, '_request', return_value=MockedResponse(True)):
            self.assertTrue(moderator.allow(comment, article, request))
            self.assertTrue(moderator.moderate(comment, article, request), "akismet should reject")
            self.assertTrue(comment.is_removed)

    @override_appsettings(
        AKISMET_API_KEY='FOOBAR',
        FLUENT_COMMENTS_AKISMET_ACTION='delete',
        FLUENT_CONTENTS_USE_AKISMET=True,
    )
    def test_akismet_delete(self, *mocks):
        """
        Test an akismet call
        """
        request = RequestFactory().post(reverse('comments-post-comment-ajax'))
        article = factories.create_article()
        comment = factories.create_comment(article=article, user_name='viagra-test-123')
        moderator = get_model_moderator(Article)  # type: FluentCommentsModerator

        self.assertTrue(article.enable_comments)
        self.assertTrue(moderator.akismet_check)  # see that settings are correctly patched

        with patch.object(Akismet, '_request', return_value=MockedResponse(True)):
            self.assertFalse(moderator.allow(comment, article, request))
            self.assertTrue(moderator.moderate(comment, article, request), "akismet should reject")
            self.assertTrue(comment.is_removed)

    @override_appsettings(FLUENT_COMMENTS_CLOSE_AFTER_DAYS=10)
    def test_comments_are_open(self):
        """
        Test that comments can auto close.
        """
        self.assertTrue(Article().comments_are_open, "article should be open for comments")
        self.assertFalse(Article(enable_comments=False).comments_are_open, "article comments should close")

        # Test ranges
        self.assertTrue(Article(publication_date=now() - timedelta(days=appsettings.FLUENT_COMMENTS_CLOSE_AFTER_DAYS - 1)).comments_are_open)
        self.assertFalse(Article(publication_date=now() - timedelta(days=appsettings.FLUENT_COMMENTS_CLOSE_AFTER_DAYS)).comments_are_open)
        self.assertFalse(Article(publication_date=now() - timedelta(days=appsettings.FLUENT_COMMENTS_CLOSE_AFTER_DAYS + 1)).comments_are_open)

    @override_appsettings(FLUENT_COMMENTS_MODERATE_AFTER_DAYS=10)
    def test_comments_are_moderated(self):
        """
        Test that moderation auto enables.
        """
        self.assertFalse(Article().comments_are_moderated, "comment should not be moderated yet")
        self.assertTrue(Article(publication_date=datetime.min).comments_are_moderated, "old comment should be moderated")

        # Test ranges
        self.assertFalse(Article(publication_date=now() - timedelta(days=appsettings.FLUENT_COMMENTS_MODERATE_AFTER_DAYS - 1)).comments_are_moderated)
        self.assertTrue(Article(publication_date=now() - timedelta(days=appsettings.FLUENT_COMMENTS_MODERATE_AFTER_DAYS)).comments_are_moderated)
        self.assertTrue(Article(publication_date=now() - timedelta(days=appsettings.FLUENT_COMMENTS_MODERATE_AFTER_DAYS + 1)).comments_are_moderated)
