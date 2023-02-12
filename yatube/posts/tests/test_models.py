from django.test import TestCase
from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='NoNameAuthor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая запись',
        )

    def post_model_have_correct_str(self):
        """Проверяем, что у модели Post корректно работает __str__."""
        post = PostModelTest.post
        self.assertEqual(post.text[:15], str(post))

    def group_model_have_correct_str(self):
        """Проверяем, что у модели Group корректно работает __str__."""
        group = PostModelTest.group
        self.assertEqual(group.title, str(group))
