"""
LinkedIn MCP Server / Watcher

Posts updates to LinkedIn to generate sales leads.
Uses LinkedIn API or browser automation via Playwright.

Note: LinkedIn automation may violate LinkedIn's Terms of Service.
For production, use the official LinkedIn Marketing API.

Setup:
1. Install Playwright: pip install playwright
2. Install browsers: playwright install chromium
3. First run will require manual login to LinkedIn

Usage:
    python linkedin_watcher.py ../Vault --post "Your post content here"

Environment Variables:
    LINKEDIN_SESSION_PATH: Path to store browser session data
    LINKEDIN_EMAIL: Your LinkedIn email
    LINKEDIN_PASSWORD: Your LinkedIn password
"""

import os
import argparse
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install")
    raise

from base_watcher import BaseWatcher


class LinkedInPost:
    """Represents a LinkedIn post to be published."""
    
    def __init__(self, content: str, image_path: Optional[str] = None, 
                 hashtags: Optional[List[str]] = None):
        self.content = content
        self.image_path = image_path
        self.hashtags = hashtags or []
        self.created = datetime.now()
        self.post_id = f'LINKEDIN_{datetime.now().strftime("%Y%m%d%H%M%S")}'
        
        # Add hashtags to content
        if self.hashtags:
            hashtag_text = ' '.join(f'#{tag}' for tag in self.hashtags)
            self.full_content = f'{content}\n\n{hashtag_text}'
        else:
            self.full_content = content
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'full_content': self.full_content,
            'image_path': self.image_path,
            'hashtags': self.hashtags,
            'post_id': self.post_id,
            'created': self.created.isoformat()
        }


class LinkedInWatcher(BaseWatcher):
    """
    Watches for content to post on LinkedIn.
    
    Can also auto-generate posts from business updates.
    """
    
    def __init__(self, vault_path: str, session_path: Optional[str] = None,
                 check_interval: int = 300, auto_post: bool = False):
        """
        Initialize the LinkedIn watcher.
        
        Args:
            vault_path: Path to the Obsidian vault root
            session_path: Path to store browser session data
            check_interval: Seconds between checks (default: 300)
            auto_post: Whether to auto-post or require approval (default: False)
        """
        super().__init__(vault_path, check_interval)
        
        # Set up session path
        if session_path:
            self.session_path = Path(session_path)
        else:
            self.session_path = os.getenv('LINKEDIN_SESSION_PATH', 
                                          str(self.logs_dir / 'linkedin_session'))
        
        self.session_path = Path(self.session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)
        
        # Auto-post setting
        self.auto_post = auto_post
        
        # Posts folder
        self.posts_folder = self.vault_path / 'Posts'
        self.posts_folder.mkdir(parents=True, exist_ok=True)
        
        # Track processed posts
        self.load_processed_ids()
        
        self.logger.info(f'Session path: {self.session_path}')
        self.logger.info(f'Auto-post: {self.auto_post}')
    
    def check_for_updates(self) -> List[LinkedInPost]:
        """
        Check for posts to publish.
        
        Looks for approved posts in Posts/Approved folder.
        
        Returns:
            List of LinkedInPost objects to publish
        """
        posts = []
        
        approved_folder = self.posts_folder / 'Approved'
        if not approved_folder.exists():
            return []
        
        for filepath in approved_folder.iterdir():
            if filepath.suffix == '.md' and filepath.name not in self.processed_ids:
                try:
                    content = filepath.read_text()
                    post = self._parse_post_file(filepath, content)
                    if post:
                        posts.append(post)
                except Exception as e:
                    self.logger.error(f'Error parsing post file {filepath}: {e}')
        
        return posts
    
    def _parse_post_file(self, filepath: Path, content: str) -> Optional[LinkedInPost]:
        """Parse a post markdown file."""
        try:
            # Extract frontmatter
            post_data = {}
            if '---' in content:
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    for line in frontmatter.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            post_data[key.strip()] = value.strip()
            
            # Extract body content
            body = content.split('---', 2)[-1].strip() if '---' in content else content
            
            # Get hashtags
            hashtags = []
            if 'hashtags:' in post_data:
                hashtags = [h.strip() for h in post_data['hashtags'].split(',')]
            
            # Get image path
            image_path = post_data.get('image_path')
            
            # Use body as content
            post_content = body
            
            return LinkedInPost(
                content=post_content,
                image_path=image_path,
                hashtags=hashtags
            )
            
        except Exception as e:
            self.logger.error(f'Error parsing post: {e}')
            return None
    
    def create_action_file(self, post: LinkedInPost) -> Optional[Path]:
        """
        Create action file for LinkedIn post.
        
        For Silver tier: Posts require approval before publishing.
        
        Args:
            post: LinkedInPost to process
            
        Returns:
            Path to created action file
        """
        try:
            # If auto-post is enabled, post directly
            if self.auto_post:
                success = self.publish_post(post)
                status = 'published' if success else 'failed'
            else:
                # Create approval request
                status = 'pending_approval'
            
            # Create post file
            action_path = self.posts_folder / f'{post.post_id}.md'
            
            content = f'''---
type: linkedin_post
post_id: {post.post_id}
created: {post.created.isoformat()}
status: {status}
hashtags: {', '.join(post.hashtags) if post.hashtags else ''}
image_path: {post.image_path or 'None'}
---

# LinkedIn Post

## Content

{post.full_content}

---

## Publishing Details

- **Created:** {post.created.strftime('%Y-%m-%d %H:%M:%S')}
- **Status:** {status}
- **Auto-Post:** {'Yes' if self.auto_post else 'No'}

---

## Instructions

### To Approve (Manual Mode)
1. Review the post content
2. Move this file to `Posts/Approved/` folder
3. The LinkedIn watcher will publish it

### To Reject
Move this file to `Posts/Rejected/` folder with a comment.

---

## Approval Status

- [ ] Content reviewed
- [ ] Hashtags verified
- [ ] Ready to publish

---

## Comments

*Add comments here*

---

## Publishing Log

*Will be filled after publishing*

'''
            action_path.write_text(content)
            
            # If auto-post, mark as processed
            if self.auto_post:
                self.save_processed_id(post.post_id)
            else:
                # Move to pending folder
                pending_folder = self.posts_folder / 'Pending'
                pending_folder.mkdir(parents=True, exist_ok=True)
                pending_path = pending_folder / f'{post.post_id}.md'
                action_path.rename(pending_path)
                return pending_path
            
            # Update dashboard
            self.update_dashboard(f'LinkedIn post created: {post.content[:50]}...')
            
            return action_path
            
        except Exception as e:
            self.logger.error(f'Error creating action file: {e}', exc_info=True)
            return None
    
    def publish_post(self, post: LinkedInPost) -> bool:
        """
        Publish a post to LinkedIn.
        
        Args:
            post: LinkedInPost to publish
            
        Returns:
            True if successful
        """
        try:
            with sync_playwright() as p:
                # Launch browser with persistent context
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=False,  # Show browser for authentication
                    args=[
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                
                # Navigate to LinkedIn
                self.logger.info('Navigating to LinkedIn...')
                page.goto('https://www.linkedin.com/feed', wait_until='networkidle')
                
                # Wait for page to load
                page.wait_for_timeout(5000)
                
                # Check if logged in
                if 'login' in page.url.lower():
                    self.logger.error('Not logged in to LinkedIn. Please login manually.')
                    # Wait for manual login
                    try:
                        page.wait_for_url('https://www.linkedin.com/feed*', timeout=60000)
                        self.logger.info('Login detected')
                    except:
                        self.logger.error('Login timeout')
                        browser.close()
                        return False
                
                # Find the post creation box
                self.logger.info('Finding post creation box...')
                
                # Click on "Start a post"
                try:
                    start_post = page.query_selector('[aria-label="Start a post"]')
                    if not start_post:
                        start_post = page.query_selector('button:has-text("Start a post")')
                    if start_post:
                        start_post.click()
                        page.wait_for_timeout(2000)
                        self.logger.info('Post dialog opened')
                except Exception as e:
                    self.logger.warning(f'Could not find post button: {e}')
                
                # Find the text input field
                self.logger.info('Finding text input...')
                
                # Try multiple selectors for the text input
                text_input = None
                selectors = [
                    '[aria-label="What do you want to talk about?"]',
                    '[aria-label="What do you want to talk about?"]',
                    'div[contenteditable="true"]',
                    'textarea'
                ]
                
                for selector in selectors:
                    try:
                        text_input = page.query_selector(selector)
                        if text_input:
                            break
                    except:
                        pass
                
                if text_input:
                    # Type the post content
                    self.logger.info('Typing post content...')
                    text_input.click()
                    page.wait_for_timeout(1000)
                    
                    # Type in chunks to avoid detection
                    for chunk in self._chunk_text(post.full_content, 50):
                        text_input.type(chunk, delay=random.randint(50, 150))
                        page.wait_for_timeout(random.randint(100, 300))
                    
                    page.wait_for_timeout(2000)
                    
                    # Upload image if provided
                    if post.image_path and Path(post.image_path).exists():
                        self.logger.info(f'Uploading image: {post.image_path}')
                        try:
                            # Find and click media upload button
                            media_button = page.query_selector('input[type="file"]')
                            if media_button:
                                media_button.set_input_files(post.image_path)
                                page.wait_for_timeout(3000)
                        except Exception as e:
                            self.logger.warning(f'Could not upload image: {e}')
                    
                    # Click Post button
                    self.logger.info('Clicking Post button...')
                    post_button = page.query_selector('button:has-text("Post")')
                    if post_button:
                        post_button.click()
                        page.wait_for_timeout(3000)
                        
                        self.logger.info(f'Post published: {post.post_id}')
                        browser.close()
                        return True
                    else:
                        self.logger.warning('Post button not found')
                else:
                    self.logger.error('Could not find text input field')
                
                browser.close()
                return False
                
        except Exception as e:
            self.logger.error(f'Error publishing post: {e}', exc_info=True)
            return False
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks for typing."""
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    def generate_post_from_update(self, update_type: str, data: Dict[str, Any]) -> LinkedInPost:
        """
        Generate a LinkedIn post from a business update.
        
        Args:
            update_type: Type of update (milestone, achievement, tip, etc.)
            data: Update data
            
        Returns:
            LinkedInPost object
        """
        templates = {
            'milestone': '''🎉 Milestone Alert!

{achievement}

We're excited to share this progress with our network. Thank you to everyone who has supported us on this journey!

#Milestone #Business #Growth''',
            
            'achievement': '''✨ Achievement Unlocked

{achievement}

This wouldn't have been possible without our amazing team and clients. Here's to continued success!

#Achievement #Success #Business''',
            
            'tip': '''💡 Quick Tip

{tip}

What's your experience with this? Share in the comments!

#Tip #Advice #Professional''',
            
            'announcement': '''📢 Announcement

{announcement}

We're excited about this new development. Stay tuned for more updates!

#Announcement #News #Business''',
            
            'testimonial': '''⭐ Client Testimonial

"{testimonial}"

We're grateful for clients like {client_name}. Thank you for trusting us with your business!

#Testimonial #ClientLove #Success'''
        }
        
        template = templates.get(update_type, templates['announcement'])
        content = template.format(**data)
        
        return LinkedInPost(
            content=content,
            hashtags=['Business', 'Professional', update_type.title()]
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='LinkedIn Watcher for AI Employee')
    parser.add_argument('vault_path', type=str, help='Path to Obsidian vault')
    parser.add_argument('--session-path', type=str, default=None,
                        help='Path to store browser session')
    parser.add_argument('--interval', type=int, default=300,
                        help='Check interval in seconds (default: 300)')
    parser.add_argument('--auto-post', action='store_true',
                        help='Enable auto-posting (requires authentication)')
    parser.add_argument('--post', type=str, default=None,
                        help='Post content (for one-time posting)')
    parser.add_argument('--hashtags', type=str, nargs='+', default=None,
                        help='Hashtags for the post')
    
    args = parser.parse_args()
    
    if args.post:
        # One-time post
        watcher = LinkedInWatcher(args.vault_path, args.session_path, auto_post=args.auto_post)
        post = LinkedInPost(args.post, hashtags=args.hashtags)
        result = watcher.publish_post(post)
        print(f'Post {"successful" if result else "failed"}')
    else:
        # Run watcher
        watcher = LinkedInWatcher(
            args.vault_path, 
            args.session_path, 
            check_interval=args.interval,
            auto_post=args.auto_post
        )
        watcher.run()


if __name__ == '__main__':
    main()
