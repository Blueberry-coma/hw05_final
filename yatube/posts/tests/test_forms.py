from django.urls import reverse
from http import HTTPStatus
from django.test import Client, TestCase, override_settings
from ..models import Group, Post, User, Comment
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import tempfile
import shutil

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

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
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовая запись',
            group=cls.group,
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

    def test_create_post_is_valid(self):
        """При отправке валидной формы создаётся новая запись в базе данных."""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'id': self.post.pk,
            'image': image
        }
        response = self.authorized_client.post(reverse(
            'posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile', kwargs={'username': self.auth_user.username}
            )
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст', 
                group=self.group.pk,
                author=self.auth_user,
                ).exists()
        )

    def test_edit_post_is_valid(self):
        """При отправке валидной формы происходит изменение поста."""
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
        }
        self.authorized_client_author.post(reverse(
            'posts:post_create'),
            data=form_data,
            follow=True
        )
        post = Post.objects.get(id=self.group.pk)
        self.authorized_client_author.get(f'/posts/{post.pk}/edit/')
        form_data = {
            'text': 'Отредактированный в форме текст',
            'group': self.group.pk,
        }
        response = self.authorized_client_author.post(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        post_edit = Post.objects.get(id=self.group.pk)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post_edit.text, 'Отредактированный в форме текст')
        self.assertEqual(post_edit.author, PostURLTests.author)
        self.assertEqual(post_edit.group, PostURLTests.group)

    def test_guest_user_create_comment(self):
        """Проверка создания комментария не авторизированным пользователем."""
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            text='Текст поста',
            author=self.author)
        form_data = {'text': 'Тестовый коментарий'}
        response = self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=True)
        redirect = reverse('login') + '?next=' + reverse(
            'posts:add_comment', kwargs={'post_id': post.id})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(response, redirect)

    def test_authorized_user_create_comment(self):
        """Проверка создания коментария авторизированным клиентом."""
        comments_count = Comment.objects.count()
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.auth_user)
        form_data = {'text': 'Тестовый коментарий'}
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=True)
        comment = Comment.objects.latest('id')
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.auth_user)
        self.assertEqual(comment.post_id, post.id)
        self.assertRedirects(
            response, reverse('posts:post_detail', args={post.id}))