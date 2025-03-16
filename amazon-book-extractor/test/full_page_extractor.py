#!/usr/bin/env python3
"""
Amazon Full Page Extractor
This script extracts book information from a complete Amazon product page HTML file
"""

from bs4 import BeautifulSoup
import json
import re
import sys
import argparse
from urllib.parse import urljoin

def extract_book_info(html_file, base_url="https://www.amazon.com"):
    """
    Extract book information from a complete Amazon product page HTML file
    """
    # Initialize the book info dictionary
    book_info = {
        'title': '',
        'author': '',
        'author_url': '',
        'publisher': '',
        'publication_date': '',
        'isbn': '',
        'cover_image_url': '',
        'description': '',
        'author_bio': '',
        'ratings': {
            'amazon_rating': '',
            'amazon_rating_count': '',
            'goodreads_rating': '',
            'goodreads_rating_count': ''
        },
        'reviews': [],
        'related_books': []
    }
    
    try:
        # Read the HTML file
        print(f"Reading HTML file: {html_file}")
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Create a BeautifulSoup object for the entire HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title_element = soup.select_one('#productTitle')
        if title_element:
            book_info['title'] = title_element.text.strip()
            print(f"Found title: {book_info['title']}")
        else:
            print("Title not found")
        
        # Extract author and author URL
        author_element = soup.select_one('#bylineInfo .author a, #bylineInfo .contributorNameID')
        if author_element:
            book_info['author'] = author_element.text.strip()
            book_info['author_url'] = urljoin(base_url, author_element.get('href', ''))
            print(f"Found author: {book_info['author']}")
            print(f"Found author URL: {book_info['author_url']}")
        else:
            print("Author not found")
        
        # Extract publisher
        publisher_element = soup.select_one('#rpi-attribute-book_details-publisher .rpi-attribute-value span, #detailBullets_feature_div li:contains("Publisher") span:nth-child(2)')
        if publisher_element:
            book_info['publisher'] = publisher_element.text.strip()
            print(f"Found publisher: {book_info['publisher']}")
        else:
            # Try alternative selector
            detail_bullets = soup.select('#detailBullets_feature_div li')
            for bullet in detail_bullets:
                text = bullet.text.strip()
                if 'Publisher' in text:
                    publisher_text = text.split(':')[-1].strip()
                    book_info['publisher'] = publisher_text
                    print(f"Found publisher (alternative): {book_info['publisher']}")
                    break
            if not book_info['publisher']:
                print("Publisher not found")
        
        # Extract publication date
        pub_date_element = soup.select_one('#rpi-attribute-book_details-publication_date .rpi-attribute-value span, #detailBullets_feature_div li:contains("Publication date") span:nth-child(2)')
        if pub_date_element:
            book_info['publication_date'] = pub_date_element.text.strip()
            print(f"Found publication date: {book_info['publication_date']}")
        else:
            # Try alternative selector
            detail_bullets = soup.select('#detailBullets_feature_div li')
            for bullet in detail_bullets:
                text = bullet.text.strip()
                if 'Publication date' in text:
                    date_text = text.split(':')[-1].strip()
                    book_info['publication_date'] = date_text
                    print(f"Found publication date (alternative): {book_info['publication_date']}")
                    break
            if not book_info['publication_date']:
                print("Publication date not found")
        
        # Extract ISBN
        isbn_element = soup.select_one('#rpi-attribute-book_details-isbn13 .rpi-attribute-value span, #detailBullets_feature_div li:contains("ISBN-13") span:nth-child(2)')
        if isbn_element:
            book_info['isbn'] = isbn_element.text.strip()
            print(f"Found ISBN: {book_info['isbn']}")
        else:
            # Try alternative selector
            detail_bullets = soup.select('#detailBullets_feature_div li')
            for bullet in detail_bullets:
                text = bullet.text.strip()
                if 'ISBN-13' in text or 'ISBN-10' in text:
                    isbn_text = text.split(':')[-1].strip()
                    book_info['isbn'] = isbn_text
                    print(f"Found ISBN (alternative): {book_info['isbn']}")
                    break
            if not book_info['isbn']:
                print("ISBN not found")
        
        # Extract cover image URL
        image_element = soup.select_one('#imgTagWrapperId img, #ebooksImgBlkFront')
        if image_element:
            # Try to get the high-resolution image URL first
            cover_url = image_element.get('data-old-hires', '')
            if not cover_url:
                # Try data-a-dynamic-image which contains JSON of image URLs
                dynamic_image = image_element.get('data-a-dynamic-image', '')
                if dynamic_image:
                    try:
                        image_dict = json.loads(dynamic_image)
                        # Get the URL with the highest resolution
                        if image_dict:
                            cover_url = max(image_dict.items(), key=lambda x: int(x[1][0]) * int(x[1][1]))[0]
                    except:
                        pass
            
            # If still no URL, fall back to the src attribute
            if not cover_url:
                cover_url = image_element.get('src', '')
            
            book_info['cover_image_url'] = cover_url
            print(f"Found cover image URL: {book_info['cover_image_url']}")
        else:
            print("Cover image not found")
        
        # Extract book description
        description_element = soup.select_one('#bookDescription_feature_div .a-expander-content, [data-a-expander-name="book_description_expander"] .a-expander-content')
        if description_element:
            book_info['description'] = description_element.get_text(separator=' ', strip=True)
            print(f"Found description: {book_info['description'][:50]}...")
        else:
            print("Description not found")
        
        # Extract author bio
        author_bio_element = soup.select_one('._about-the-author-card_carouselItemStyles_expander__3Fm-M .a-cardui-content, #authorBio_feature_div .a-cardui-content')
        if author_bio_element:
            book_info['author_bio'] = author_bio_element.get_text(separator=' ', strip=True)
            print(f"Found author bio: {book_info['author_bio'][:50]}...")
        else:
            print("Author bio not found")
        
        # Extract Amazon ratings
        amazon_rating_element = soup.select_one('#acrPopover .a-size-base, #averageCustomerReviews .a-size-base')
        if amazon_rating_element:
            book_info['ratings']['amazon_rating'] = amazon_rating_element.text.strip()
            print(f"Found Amazon rating: {book_info['ratings']['amazon_rating']}")
        else:
            print("Amazon rating not found")
        
        # Extract Amazon rating count
        amazon_rating_count_element = soup.select_one('#acrCustomerReviewText')
        if amazon_rating_count_element:
            book_info['ratings']['amazon_rating_count'] = amazon_rating_count_element.text.strip()
            print(f"Found Amazon rating count: {book_info['ratings']['amazon_rating_count']}")
        else:
            print("Amazon rating count not found")
        
        # Extract Goodreads ratings
        goodreads_rating_element = soup.select_one('.gr-review-rating-text .a-size-base')
        if goodreads_rating_element:
            book_info['ratings']['goodreads_rating'] = goodreads_rating_element.text.strip()
            print(f"Found Goodreads rating: {book_info['ratings']['goodreads_rating']}")
        else:
            print("Goodreads rating not found")
        
        # Extract Goodreads rating count
        goodreads_rating_count_element = soup.select_one('.gr-review-count-text .a-size-base')
        if goodreads_rating_count_element:
            book_info['ratings']['goodreads_rating_count'] = goodreads_rating_count_element.text.strip()
            print(f"Found Goodreads rating count: {book_info['ratings']['goodreads_rating_count']}")
        else:
            print("Goodreads rating count not found")
        
        # Extract reader reviews
        review_elements = soup.select('#cm-cr-dp-review-list .a-section.celwidget, .review-views .review')
        print(f"Found {len(review_elements)} review elements")
        
        # Limit to top 10 reviews
        extracted_reviews = []
        for i, review_element in enumerate(review_elements):
            review = {}
            
            # Extract reviewer name
            reviewer_element = review_element.select_one('.a-profile-name')
            if reviewer_element:
                review['reviewer_name'] = reviewer_element.text.strip()
            else:
                review['reviewer_name'] = "Anonymous"
            
            # Extract review rating
            rating_element = review_element.select_one('i.review-rating, .a-icon-star')
            if rating_element:
                rating_text = rating_element.text.strip()
                # Extract the numeric rating from text like "5.0 out of 5 stars"
                rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
                else:
                    # Try to extract from class name like "a-star-4"
                    class_str = ' '.join(rating_element.get('class', []))
                    rating_match = re.search(r'a-star-(\d+)', class_str)
                    if rating_match:
                        review['rating'] = rating_match.group(1)
                    else:
                        review['rating'] = ""
            else:
                review['rating'] = ""
            
            # Extract review title
            title_element = review_element.select_one('.review-title, .review-title-content')
            if title_element:
                review['title'] = title_element.text.strip()
            else:
                review['title'] = ""
            
            # Extract review date
            date_element = review_element.select_one('.review-date')
            if date_element:
                review['date'] = date_element.text.strip()
            else:
                review['date'] = ""
            
            # Extract review content
            content_element = review_element.select_one('.review-text, .review-text-content')
            if content_element:
                review['content'] = content_element.get_text(separator=' ', strip=True)
            else:
                review['content'] = ""
            
            # Extract helpful votes
            helpful_element = review_element.select_one('.cr-vote-text')
            if helpful_element:
                review['helpful_votes'] = helpful_element.text.strip()
            else:
                review['helpful_votes'] = ""
            
            # Check if this review is a duplicate
            is_duplicate = False
            for existing_review in extracted_reviews:
                if (review['reviewer_name'] == existing_review['reviewer_name'] and 
                    review['title'] == existing_review['title'] and
                    review['content'] == existing_review['content']):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                extracted_reviews.append(review)
                print(f"Found review {len(extracted_reviews)}: {review['title'][:30]}...")
                
                # Stop after extracting 10 unique reviews
                if len(extracted_reviews) >= 10:
                    break
        
        # Add the unique reviews to the book_info
        book_info['reviews'] = extracted_reviews
        print(f"Total unique reviews extracted: {len(book_info['reviews'])}")
        
        # Extract related books
        # First try carousel cards
        related_books_elements = soup.select('.a-carousel-card')
        print(f"Found {len(related_books_elements)} carousel elements")
        
        # Process all potential book elements
        for element in related_books_elements:
            link_element = element.select_one('a[href*="/dp/"]')
            image_element = element.select_one('img')
            title_element = element.select_one('.a-truncate, .p13n-sc-truncate')
            
            if link_element and image_element:
                title_text = ''
                if title_element:
                    full_title = title_element.select_one('.a-truncate-full')
                    if full_title:
                        title_text = full_title.text.strip()
                    else:
                        title_text = title_element.text.strip()
                elif image_element.get('alt'):
                    title_text = image_element.get('alt', '').strip()
                
                url = link_element.get('href', '')
                image_url = image_element.get('src', '')
                
                # Only add if we have a valid URL and either a title or image
                if url and (title_text or image_url):
                    # Check if this book is already in our list (avoid duplicates)
                    is_duplicate = False
                    for existing_book in book_info['related_books']:
                        if url in existing_book['url'] or (title_text and title_text == existing_book['title']):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        related_book = {
                            'title': title_text,
                            'url': urljoin(base_url, url),
                            'image_url': image_url
                        }
                        book_info['related_books'].append(related_book)
                        print(f"Found related book: {related_book['title'] or 'Untitled'}")
        
        # If we didn't find enough related books, try other selectors
        if len(book_info['related_books']) < 3:
            print("Trying alternative selectors for related books...")
            
            # Try different selectors that might contain book information
            potential_book_elements = []
            potential_book_elements.extend(soup.select('div[data-asin]'))
            potential_book_elements.extend(soup.select('div.p13n-sc-uncoverable-faceout'))
            potential_book_elements.extend(soup.select('li.a-carousel-card'))
            potential_book_elements.extend(soup.select('div._mes-dp_styles_recommendation__1dnoX'))
            
            print(f"Found {len(potential_book_elements)} potential book elements")
            
            for element in potential_book_elements:
                # Skip if this element has already been processed
                if element in related_books_elements:
                    continue
                
                # Try to extract book information from this element
                link_element = element.select_one('a[href*="/dp/"]') or element.select_one('a[id]')
                image_element = element.select_one('img')
                title_element = element.select_one('.a-truncate, .p13n-sc-truncate, span[class*="truncate"], div[class*="title"]')
                
                if not link_element and 'data-asin' in element.attrs:
                    # Try to find links within this element
                    links = element.select('a')
                    for link in links:
                        href = link.get('href', '')
                        if '/dp/' in href or 'product' in href:
                            link_element = link
                            break
                
                # Extract title from various possible elements
                title_text = ''
                if title_element:
                    full_title = title_element.select_one('.a-truncate-full')
                    if full_title:
                        title_text = full_title.text.strip()
                    else:
                        title_text = title_element.text.strip()
                elif image_element and image_element.get('alt'):
                    # Use image alt text as title if available
                    title_text = image_element.get('alt', '').strip()
                
                # Only add if we have at least a title and a link
                if (title_text and link_element) or (image_element and link_element):
                    url = link_element.get('href', '')
                    image_url = ''
                    if image_element:
                        image_url = image_element.get('src', '')
                    
                    # If title is still empty but we have an image with alt text
                    if not title_text and image_element and image_element.get('alt'):
                        title_text = image_element.get('alt', '').strip()
                    
                    # If we still don't have a title, try to extract from the URL
                    if not title_text and '/dp/' in url:
                        # Extract title from URL if possible
                        url_parts = url.split('/')
                        if len(url_parts) > 3:
                            title_index = url_parts.index('dp') - 1 if 'dp' in url_parts else -3
                            if title_index >= 0 and title_index < len(url_parts):
                                title_text = url_parts[title_index].replace('-', ' ').title()
                    
                    # Only add if we have a valid URL and either a title or image
                    if url and (title_text or image_url):
                        # Check if this book is already in our list (avoid duplicates)
                        is_duplicate = False
                        for existing_book in book_info['related_books']:
                            if url in existing_book['url'] or (title_text and title_text == existing_book['title']):
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            related_book = {
                                'title': title_text,
                                'url': urljoin(base_url, url),
                                'image_url': image_url
                            }
                            book_info['related_books'].append(related_book)
                            print(f"Found related book: {related_book['title'] or 'Untitled'}")
        
        print(f"Total related books found: {len(book_info['related_books'])}")
        return book_info
    
    except Exception as e:
        print(f"Error extracting book info: {e}")
        import traceback
        traceback.print_exc()
        return {'error': f'Failed to extract book information: {str(e)}'}

def main():
    parser = argparse.ArgumentParser(description='Extract book information from a complete Amazon product page HTML file')
    parser.add_argument('html_file', help='Path to the HTML file')
    parser.add_argument('--base_url', '-b', default='https://www.amazon.com', help='Base URL for resolving relative URLs')
    parser.add_argument('--output', '-o', help='Output file path (JSON format)')
    args = parser.parse_args()
    
    book_info = extract_book_info(args.html_file, args.base_url)
    
    # Print the result
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(book_info, f, ensure_ascii=False, indent=2)
        print(f"Book information saved to {args.output}")
    else:
        print(json.dumps(book_info, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
