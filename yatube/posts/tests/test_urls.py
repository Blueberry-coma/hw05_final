from http import HTTPStatus
from django.test import Client, TestCase
from django.urls import reverse
from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='NoNameAuthor')
        cls.auth_user = User.objects.create(username='AuthUser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug_test',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовая запись',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_author = Client()
        self.authorized_client.force_login(PostURLTests.auth_user)
        self.authorized_client_author.force_login(PostURLTests.author)

    def test_index(self):
        """Сайт работает."""
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_404(self):
        """Запрос к несуществующей странице."""
        response = self.guest_client.get('/page_404/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_url_exists_at_desired_location_for_anonymous(self):
        """Страница доступна всем."""
        url_names = (
            '/',
            '/group/slug_test/',
            '/profile/NoNameAuthor/',
            f'/posts/{self.post.pk}/',
        )
        for address in url_names:
            with self.subTest():
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_exists_at_desired_location_for_author(self):
        """Страница доступна автору."""
        response = self.authorized_client_author.get(
            f'/posts/{self.post.pk}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_exists_at_desired_location_for_auth_user(self):
        """Страница доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous_on_admin_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        login_url = reverse('users:login')
        create_url = reverse('posts:post_create')
        redirect_url = f'{login_url}?next={create_url}'
        response = self.guest_client.get(reverse(
            'posts:post_create'))
        self.assertRedirects(
            response, redirect_url)

    def test_urls_uses_correct_template(self):
        """Проверяем, что URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': '/group/slug_test/',
            'posts/profile.html': '/profile/NoNameAuthor/',
            'posts/post_detail.html': f'/posts/{self.post.pk}/',
            'posts/create_post.html': '/create/',
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_post_detail_url_redirect_anonymous_on_admin_login(self):
        """Страница /posts/1/edit/ перенаправит анонимного пользователя
        на страницу логина.
        """
        login_url = reverse('users:login')
        edit_url = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        redirect_url = f'{login_url}?next={edit_url}'
        response = self.guest_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}))
        self.assertRedirects(response, redirect_url)
