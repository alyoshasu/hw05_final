# Каждый логический набор тестов — это класс,
# который наследуется от базового класса TestCase
from django.test import TestCase, Client
from posts.models import Group, Post
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

# Каждый класс — это набор тестов. Имя такого класса принято начинать со слова Test.
# В файле может быть множество наборов тестов,
# не обязательно иметь один класс для всего приложения.


def find_post(self, response, text, author):
    self.assertEqual(response.context["user"].username, author)

    if "page" in response.context:
        self.assertEqual(response.context["page"].object_list[0].text, text)
    else:
        self.assertEqual(response.context["post"].text, text)


class TestStringMethods(TestCase):
    def setUp(self):
        print("SetUp")
        self.user = User.objects.create_user(
            username="sarah", email="connor.s@skynet.com", password="12345"
        )

        self.authorized_client = Client()
        self.unauthorized_client = Client()

        self.authorized_client.force_login(self.user)

        self.group = Group.objects.create(
            slug="Test_slug",
            title="Test_title",
            description="Test_description",
        )

    def test_profile(self):
        response = self.authorized_client.get(reverse('profile', args=[self.user.username]))
        self.assertEqual(response.status_code, 200)

    def test_new_post_user(self):
        response = self.authorized_client.post(
            reverse('post_new'),
            {
                'text': 'Текст',
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)
        response = self.authorized_client.post(reverse('index'))
        find_post(self, response, 'Текст', self.user.username)

    def test_new_post_not_user(self):
        response = self.unauthorized_client.post(reverse('post_new'), {'text': 'Текст'})
        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("post_new")}'
        )
        self.assertEqual(Post.objects.count(), 0)

    def test_new_post_pages(self):
        self.post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Hello world!',
        )

        urls = [
            reverse('index'),
            reverse('profile', args=[self.user.username]),
            reverse('post', args=[self.user.username, self.post.pk]),
        ]

        for url in urls:
            response = self.authorized_client.post(url)
            find_post(self, response, self.post.text, self.user.username)

    def test_post_edit(self):
        self.post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Hello world!',
        )

        response = self.authorized_client.post(
            reverse('post_edit', args=[self.user.username, self.post.pk]),
            {'text': 'Текст12345'}
        )
        self.assertRedirects(response, reverse('post', args=[self.user.username, self.post.pk]))

        urls = [
            reverse('index'),
            reverse('profile', args=[self.user.username]),
            reverse('post', args=[self.user.username, self.post.pk]),
        ]

        for url in urls:
            response = self.authorized_client.post(url)
            find_post(self, response, 'Текст12345', self.user.username)

    def test_404(self):
        response = self.authorized_client.get(
            'never_existed_page_404'
        )
        self.assertEqual(response.status_code, 404)

    def test_post_with_image(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile(
            name='some.gif',
            content=small_gif,
            content_type='image/gif',
        )

        post = Post.objects.create(
            author=self.user,
            text='text',
            image=img,
            group=self.group,
        )

        urls = [
            reverse('index'),
            reverse('post', args=[self.user.username, post.id]),
            reverse('profile', args=[self.user.username]),
            reverse('group_post', args=[self.group.slug])
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertContains(response, '<img')

    def test_post_without_image(self):
        not_image = SimpleUploadedFile(
            name='some.txt',
            content=b'abc',
            content_type='text/plain',
        )

        url = reverse('post_new')
        response = self.authorized_client.post(
            url,
            {
                'text': 'some_text',
                'image': not_image,
            }
        )

        self.assertFormError(
            response,
            'form',
            'image',
            errors=(
                'Загрузите правильное изображение. '
                'Файл, который вы загрузили, '
                'поврежден или не является изображением.'
            ),
        )

    def test_cache(self):
        url = reverse('index')
        self.post_1 = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Hello world!',
        )
        response_1 = self.authorized_client.post(url)
        self.post_2 = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Buy world!',
        )
        response_2 = self.authorized_client.post(url)
        self.assertEqual(response_1, response_2)

    def tearDown(self):
        print("tearDown")
