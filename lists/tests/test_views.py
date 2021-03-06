from django.shortcuts import render

from django.test import TestCase
from django.urls import resolve, reverse
from django.http import HttpRequest
from django.utils.html import escape

from lists.views import home_page
from lists.forms import (
	DUPLICATE_ITEM_ERROR, EMPTY_ITEM_ERROR,
	ExistingListItemForm, ItemForm,
)

import lists.views

from lists.models import Item, List

import bs4

from unittest import skip

class BasicTestCase(TestCase):
	def validate_html_structure(self, response, expected_h1_text, expected_action_uri):
		self.assertEqual(response.status_code, 200)
		content_type = response['Content-Type'].split(';')[0]
		self.assertEqual(content_type, 'text/html')

		soup = bs4.BeautifulSoup(response.content, 'lxml')

		html_tags = soup.findAll('html')
		self.assertEqual(len(html_tags), 1, msg='expected one and only one <html> tag')
		title_tags = html_tags[0].findAll('title')
		self.assertEqual(len(title_tags), 1, msg='expected one and only one <title> tag')
		title_tag = title_tags[0]
		self.assertEqual(str(title_tag.string), 'To-Do lists')
		body_tags = html_tags[0].findAll('body')
		self.assertEqual(len(body_tags), 1, msg='expected one and only one <body> tag')
		h1_tags = body_tags[0].findAll('h1')
		self.assertEqual(len(h1_tags), 1, msg='expected one and only one <h1> tag')
		h1_tag = h1_tags[0]
		self.assertEqual(str(h1_tag.string), expected_h1_text, msg='incorrect text for h1 tag')
		form_tags = body_tags[0].findAll('form')
		self.assertEqual(len(form_tags), 2, msg='expected two <form> tags')
		form_tag = form_tags[1]
		form_tag_attrs = form_tag.attrs
		self.assertEqual(form_tag_attrs['method'], 'POST', msg='expected form method POST')
		self.assertEqual(form_tag_attrs['action'], expected_action_uri, msg='expected correct action uri')

		return soup

class ListViewTest(BasicTestCase):

#	from django.urls import resolve

	def test_manual_correct_list_id_uri(self):
		alist = List.objects.create()
		correct_list_uri = f'/lists/{alist.id}/'
		self.assertEqual(correct_list_uri, alist.get_absolute_url())

	def test_manual_uri_resolves_to_list_view(self):
		view, args, kwargs = resolve('/lists/321/')
		self.assertEqual(view, lists.views.view_list)
		self.assertEqual(321, int(args[0]))

	def test_list_id_uri_resolves_to_list_view(self):
		alist = List.objects.create()
		view, args, kwargs = resolve(alist.get_absolute_url())
		self.assertEqual(view, lists.views.view_list)
		self.assertEqual(int(args[0]), alist.id)

	def test_uses_list_template(self):
		alist = List.objects.create()
		response = self.client.get(alist.get_absolute_url())
		self.assertTemplateUsed(response, 'lists.html')

	def test_display_item_form(self):
		list_ = List.objects.create()
		response = self.client.get(f'/lists/{list_.id}/')
		self.assertIsInstance(response.context['form'], ExistingListItemForm)
		self.assertContains(response, 'name="text"')

	def test_list_uri_action_new_list(self):
		expected_action_uri = '/lists/new'
		action_uri = reverse('new_list')
		self.assertEqual(action_uri, expected_action_uri)

	def test_list_view_html(self):
		response = self.client.get('/')
		alist = List.objects.create()
		### how to create URI for list item?
		### how to create URI for list/add_item?
		### how to manage these and pass these into the templates, etc?
		list_uri = f'/lists/{alist.id}/'
		add_item_uri = list_uri
		response = self.client.get(list_uri)
		soup = self.validate_html_structure(response, expected_h1_text='Your To-Do list', expected_action_uri=add_item_uri)
		table_tags = soup.findAll('table')
		self.assertEqual(len(table_tags), 1, msg='expected one and only one <table> tag')

	def test_displays_only_items_for_that_list(self):
		correct_list = List.objects.create()
		Item.objects.create(text='item one', list=correct_list)
		Item.objects.create(text='item two', list=correct_list)
		other_list = List.objects.create()
		Item.objects.create(text='other list item one', list=other_list)
		Item.objects.create(text='other list item two', list=other_list)

		response = self.client.get(correct_list.get_absolute_url())

		self.assertContains(response, 'item one')
		self.assertContains(response, 'item two')
		self.assertNotContains(response, 'other list item one')
		self.assertNotContains(response, 'other list item two')

	def test_passes_correct_list_to_template(self):
		other_list = List.objects.create()
		correct_list = List.objects.create()
		response = self.client.get(correct_list.get_absolute_url())
		self.assertEqual(response.context['list'], correct_list)


	def test_manual_uri_resolves_to_view_list(self):
		view, args, kwargs = resolve('/lists/3/')
		self.assertEqual(view, lists.views.view_list)

	def test_add_item_uri_resolves_to_view_list(self):
		other_list = List.objects.create()
		correct_list = List.objects.create()

		view, args, kwargs = resolve(correct_list.get_absolute_url())
		self.assertEqual(view, lists.views.view_list)
		self.assertEqual(int(args[0]), correct_list.id)

	def test_can_save_a_POST_request_to_an_existing_list(self):
		other_list = List.objects.create()
		correct_list = List.objects.create()

		self.client.post(correct_list.get_absolute_url(), data={'text':'A new item for an existing list'})

		self.assertEqual(Item.objects.count(), 1)
		new_item = Item.objects.first()
		self.assertEqual(new_item.text, 'A new item for an existing list')
		self.assertEqual(new_item.list, correct_list)

	def test_POST_redirects_to_list_view(self):
		other_list = List.objects.create()
		correct_list = List.objects.create()

		response = self.client.post(correct_list.get_absolute_url(), data={'text': 'A new item for an existing list'})

		self.assertRedirects(response, correct_list.get_absolute_url())

	def post_invalid_input(self):
		list_ = List.objects.create()
		return self.client.post(f'/lists/{list_.id}/', data={'text':''})

	def test_for_invalid_input_nothing_saved_to_db(self):
		self.post_invalid_input()
		self.assertEqual(Item.objects.count(), 0)

	def test_for_invalid_input_renders_list_template(self):
		response = self.post_invalid_input()
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'lists.html')

	def test_for_invalid_input_passes_form_to_template(self):
		response = self.post_invalid_input()
		self.assertIsInstance(response.context['form'], ExistingListItemForm)

	def test_for_invalid_input_shows_error_on_page(self):
		response = self.post_invalid_input()
		self.assertContains(response, escape(EMPTY_ITEM_ERROR))

	def test_duplicate_item_validation_errors_end_up_on_lists_page(self):
		list1 = List.objects.create()
		item1 = Item.objects.create(list=list1, text='textey')
		response = self.client.post(f'/lists/{list1.id}/', data={'text': 'textey'})
		expected_error = escape(DUPLICATE_ITEM_ERROR)
		self.assertContains(response, expected_error)
		self.assertTemplateUsed(response, 'lists.html')
		self.assertEqual(Item.objects.all().count(), 1)

class HomePageTest(BasicTestCase):

	def test_base_template(self):
		request = HttpRequest()
		response = render(request, 'base_example.html')
		soup = self.validate_html_structure(response, expected_h1_text='Example Header Text', expected_action_uri='/lists/example_form_action_uri')
		table_tags = soup.findAll('table')
		self.assertEqual(len(table_tags), 1, msg='expected one and only one <table> tag')

	def test_home_html(self):
		response = self.client.get('/')
		soup = self.validate_html_structure(response, expected_h1_text='Start a new To-Do list', expected_action_uri='/lists/new')

	def test_uses_home_template(self):
		response = self.client.get('/')
		self.assertTemplateUsed(response, 'home.html')

	def test_home_page_uses_item_form(self):
		response = self.client.get('/')
		self.assertIsInstance(response.context['form'], ItemForm)

class NewListTest(TestCase):
	def test_can_save_a_POST_request(self):
		item_text_value = 'A new list item'
		action_uri = reverse('new_list')
		self.assertEqual(action_uri, '/lists/new')
		response = self.client.post(action_uri, data={'text':item_text_value})

		self.assertEqual(Item.objects.count(), 1)
		new_item = Item.objects.first()
		self.assertEqual(new_item.text, item_text_value)

	def test_redirects_after_POST(self):
		action_uri = reverse('new_list')
		self.assertEqual(action_uri, '/lists/new')
		response = self.client.post(action_uri, data={'text':'A new list item'})
		new_list = List.objects.first()
		self.assertRedirects(response, new_list.get_absolute_url())

	def test_for_invalid_input_renders_home_template(self):
		response = self.client.post('/lists/new', data={'text':''})
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'home.html')

	def test_validation_errors_are_shown_on_home_page(self):
		response = self.client.post('/lists/new', data={'text':''})
#		expected_error = escape("You can't have an empty list item")
		self.assertContains(response, escape(EMPTY_ITEM_ERROR))

	def test_for_invalid_input_passes_form_to_template(self):
		response = self.client.post('/lists/new', data={'text':''})
		self.assertIsInstance(response.context["form"], ItemForm)

	def test_invalid_list_items_are_not_saved(self):
		action_uri = reverse('new_list')
		self.assertEqual(action_uri, '/lists/new')
		self.client.post(action_uri, data={'text':''})
		self.assertEqual(List.objects.count(), 0)
		self.assertEqual(Item.objects.count(), 0)


