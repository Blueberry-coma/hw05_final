from django.urls import reverse
from django import forms
from django.test import Client, TestCase, override_settings
from ..models import Group, Post, User, Follow
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.cache import cache
import tempfile
import shutil

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class Paginator_view_test(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='NoNameAuthor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.posts = [
            Post(
                text=f'Тестовый пост {i}',
                author=cls.author,
                group=cls.group,
            )
            for i in range(13)
        ]
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.unauthorized_client = Client()

    def test_pagination(self):
        """На первой странице 10 постов, на второй 13."""
        page_one = 10
        page_two = 3
        pages_url = [
            reverse(
                'posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={
                'username': self.author.username}),
        ]
        for reverse_ in pages_url:
            with self.subTest(reverse_=reverse_):
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_).context.get('page_obj')),
                    page_one
                )
                self.assertEqual(len(self.unauthorized_client.get(
                    reverse_ + '?page=2').context.get('page_obj')),
                    page_two
                )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='NoNameAuthor')
        cls.auth_user = User.objects.create(username='AuthUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
            image=cls.image,
        )

    @classmethod
    def tearDownClass(cls):
        """Удаляем тестовые медиа."""
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_author = Client()
        self.authorized_client.force_login(PostURLTests.auth_user)
        self.authorized_client_author.force_login(PostURLTests.author)

    def test_create_post_edit_show_correct_context(self):
        """Шаблон редактирования поста create_post сформирован
        с правильным контекстом.
        """
        url = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        response = self.authorized_client_author.get(url)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for field, expected in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context(self):
        """Шаблон  create_post сформирован
        с правильным контекстом.
        """
        url = reverse('posts:post_create')
        response = self.authorized_client.get(url)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for field, expected in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context.get('form').fields.get(field)
                self.assertIsInstance(form_field, expected)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse('posts:profile', kwargs={
                'username': self.post.author}
            ): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={
                'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={
                    'post_id': self.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post_text = response.context.get('page_obj')[0].text
        post_author = response.context.get('page_obj')[0].author.username
        group_post = response.context.get('page_obj')[0].group.title
        self.assertEqual(post_text, 'Тестовый пост')
        self.assertEqual(post_author, 'NoNameAuthor')
        self.assertEqual(group_post, 'Тестовая группа')

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        url = reverse('posts:group_list', kwargs={
            'slug': self.group.slug}
        )
        response = self.authorized_client.get(url)
        group_title = response.context.get('group').title
        group_description = response.context.get('group').description
        group_slug = response.context.get('group').slug
        self.assertEqual(group_title, 'Тестовая группа')
        self.assertEqual(group_description, 'Тестовое описание')
        self.assertEqual(group_slug, 'test-slug')

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        url = reverse('posts:profile', kwargs={
            'username': PostURLTests.author})
        response = self.authorized_client_author.get(url)
        post_text = response.context.get('page_obj')[0].text
        post_author = response.context.get('page_obj')[0].author.username
        group_post = response.context.get('page_obj')[0].group.title
        self.assertEqual(post_text, 'Тестовый пост')
        self.assertEqual(post_author, 'NoNameAuthor')
        self.assertEqual(group_post, 'Тестовая группа')

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        url = reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        response = self.authorized_client_author.get(url)
        post_text = response.context.get('post').text
        post_author = response.context.get('post').author.username
        group_post = response.context.get('post').group.title
        self.assertEqual(post_text, 'Тестовый пост')
        self.assertEqual(post_author, 'NoNameAuthor')
        self.assertEqual(group_post, 'Тестовая группа')

    def test_cache(self):
        """Проверка работы кэша."""
        post = Post.objects.create(
            author=self.auth_user,
            text='Пост для проверки кэша',
            group=self.group
        )
        response_1 = self.client.get(reverse('posts:index'))
        self.assertTrue(Post.objects.get(pk=post.id))
        Post.objects.get(pk=post.id).delete()
        cache.clear()
        response_2 = self.client.get(reverse('posts:index'))
        self.assertNotEqual(response_1.content, response_2.content)

    def test_follow(self):
        """Тестирование подписки на автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='Lermontov')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        follow = Follow.objects.last()
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(follow.author, new_author)

    def test_unfollow(self):
        """Тестирование отписки от автора."""
        count_follow = Follow.objects.count()
        new_author = User.objects.create(username='Lermontov')
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': new_author.username}
            )
        )
        self.assertEqual(Follow.objects.count(), count_follow)
