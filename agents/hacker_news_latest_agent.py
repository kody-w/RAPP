from agents.basic_agent import BasicAgent
import requests

class HackerNewsLatestAgent(BasicAgent):
    def __init__(self):
        self.name = "HackerNewsLatest"
        self.metadata = {
            "name": self.name,
            "description": "Fetches the latest top stories from Hacker News and returns their titles and URLs. Use this to stay updated on trending tech news, programming discussions, and startup stories from the HN community.",
            "parameters": {
                "type": "object",
                "properties": {
                    "story_limit": {
                        "type": "integer",
                        "description": "Number of latest top stories to retrieve (recommended: 5-10 for quick scan, 20-30 for deep dive)",
                        "default": 10
                    }
                },
                "required": ["story_limit"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, story_limit=10):
        """
        Fetches top stories from Hacker News API.

        Args:
            story_limit: Number of stories to retrieve (default: 10)

        Returns:
            Formatted string with story titles and URLs
        """
        try:
            # Get top story IDs
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            story_ids = resp.json()[:story_limit]

            stories = []
            for sid in story_ids:
                # Get story details
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                item_resp = requests.get(item_url, timeout=10)
                item_resp.raise_for_status()
                data = item_resp.json()

                title = data.get("title", "No title")
                link = data.get("url", f"https://news.ycombinator.com/item?id={sid}")
                score = data.get("score", 0)

                # Format with score for context
                stories.append(f"🔥 {title}\n   {score} points - {link}")

            return f"📰 **Top {len(stories)} Hacker News Stories:**\n\n" + "\n\n".join(stories)

        except requests.exceptions.RequestException as e:
            return f"❌ Error fetching Hacker News stories: {str(e)}\n\nPlease check your internet connection and try again."
        except Exception as e:
            return f"❌ Unexpected error: {str(e)}"
