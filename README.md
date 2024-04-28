```python
class Me:

    def __init__(self):
        self.name = "Nurzhanat Zhussup"
        
class About(Me):

    def __init__(self):
        super().__init__
        
        self.university = "Vienna University of Economics and Business"
        self.degree = "BSc. Business, Economics and Social Sciences"
        self.specialization = "Data Science"
        self.city = "Vienna"
 
    def contact(self) -> dict:
        return {
            "LinkedIn": "https://www.linkedin.com/in/nurzhanat-zhussup/",
            "E-Mail": "zhussup.nb@gmail.com"
        }

    def get_skills(self) -> dict:
        return {
            "Programming": ["Python", "R", "Java"],
            "Data Science": ["Machine Learning", "Deep Learning", "Big Data", "Data Processing"]
        }
        
    def get_projects(self) -> str:
        return "https://github.com/koettbullarr?tab=repositories"
```
    
