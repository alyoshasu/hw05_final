from django.test import TestCase, Client
from posts.models import Group, Post, Follow
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

import time


def not_find_post(self, response, text, author):
    if "page" in response.context:
        self.assertEqual(response.context["page"].object_list.count(), 0)
    else:
        self.assertEqual(response.context["post"].count(), 0)


def find_post(self, response, text, author):
    if "page" in response.context:
        self.assertEqual(response.context["page"].object_list[0].text, text)
        self.assertEqual(
            response.context["page"].object_list[0].author.username,
            author,
        )
    else:
        self.assertEqual(response.context["post"].text, text)
        self.assertEqual(response.context["post"].author.username, author)


def not_find_comment(self, response):
    self.assertNotContains(response, "items")


def find_comment(self, response, author, text):
    self.assertContains(response, "items")
    self.assertEqual(response.context["items"][0].text, text)
    self.assertEqual(response.context["items"][0].author.username, author)


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
        response = self.authorized_client.get(
            reverse('profile',
                    args=[self.user.username],
                    )
        )
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
        response = self.unauthorized_client.post(
            reverse('post_new'),
            {'text': 'Текст'},
        )
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
        self.assertRedirects(
            response,
            reverse(
                'post',
                args=[self.user.username, self.post.pk],
            )
        )

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
            # reverse('index'), - не найдёт из-за кеширования
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
            text='Текст 13254235236336!',
        )
        print(1)
        response_1 = self.authorized_client.get(url)
        self.assertEqual(response_1.context["page"].object_list, [self.post_1])
        self.post_2 = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Текст 83762782982723!',
        )
        print(2)
        response_2 = self.authorized_client.get(url)
        self.assertEqual(response_2.context, None)
        time.sleep(6)
        print(3)
        response_3 = self.authorized_client.get(url)
        self.assertEqual(
            response_3.context["page"].object_list,
            [self.post_2, self.post_1],
        )

    def test_auth_user_follow_and_unfollow(self):
        self.second_user = User.objects.create_user(
            username="second_user",
            email="second_user@skynet.com",
            password="012345",
        )
        self.post = Post.objects.create(
            author=self.second_user,
            group=self.group,
            text='Hello world!',
        )

        self.assertEqual(self.user.follower.all().count(), 0)

        url_1 = reverse('profile_follow', args=[self.second_user.username])
        response = self.authorized_client.get(url_1)
        self.assertEqual(self.user.follower.all().count(), 1)

        url_2 = reverse('profile_unfollow', args=[self.second_user.username])
        response = self.authorized_client.get(url_2)
        self.assertEqual(self.user.follower.all().count(), 0)

    def test_new_post_feed(self):
        self.second_user = User.objects.create_user(
            username="second_user",
            email="second_user@skynet.com",
            password="012345",
        )

        self.post = Post.objects.create(
            author=self.second_user,
            group=self.group,
            text='Hello world!',
        )

        url = reverse('follow_index')
        response_1 = self.authorized_client.post(url)
        not_find_post(
            self,
            response_1,
            self.post.text,
            self.second_user.username,
        )

        Follow.objects.create(
            user=self.user,
            author=self.second_user
        )

        response_2 = self.authorized_client.post(url)
        find_post(self, response_2, self.post.text, self.second_user.username)

        Follow.objects.get(user=self.user).delete()
        response_3 = self.authorized_client.post(url)
        not_find_post(
            self,
            response_1,
            self.post.text,
            self.second_user.username,
        )

    def test_auth_user_comments(self):
        self.second_user = User.objects.create_user(
            username="second_user",
            email="second_user@skynet.com",
            password="012345",
        )

        self.post = Post.objects.create(
            author=self.second_user,
            group=self.group,
            text='Hello world!',
        )

        url = reverse(
            'add_comment',
            args=[self.second_user.username, self.post.pk],
        )
        response_1 = self.authorized_client.post(
            url,
            {'text': 'aaaaaaa'},
            follow=True,
        )
        find_comment(self, response_1, self.user.username, 'aaaaaaa')
        response_2 = self.unauthorized_client.post(
            url,
            {'text': 'aaaaaaa'},
            follow=True,
        )
        not_find_comment(self, response_2)

    def tearDown(self):
        print("tearDown")
