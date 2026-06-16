"""
Text summarization module for Nexcomply application
Uses T5 model for generating summaries
"""

from transformers import T5Tokenizer, T5ForConditionalGeneration
import torch


class TextSummarizer:
    """Class to handle text summarization operations"""
    
    def __init__(self, model_name="t5-small"):
        """
        Initialize summarizer with T5 model
        
        Args:
            model_name: Name of the T5 model to use
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load T5 model and tokenizer"""
        try:
            self.tokenizer = T5Tokenizer.from_pretrained(self.model_name)
            self.model = T5ForConditionalGeneration.from_pretrained(self.model_name)
        except Exception as e:
            print(f"Error loading T5 model: {str(e)}")
    
    def summarize(self, text, max_length=150, min_length=50, 
                  num_beams=4, length_penalty=2.0):
        """
        Summarize text using T5 model
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            min_length: Minimum length of summary
            num_beams: Number of beams for beam search
            length_penalty: Length penalty for generation
            
        Returns:
            str: Summary of the text
        """
        if not text or not self.model or not self.tokenizer:
            return "Unable to generate summary"
        
        try:
            # Prepare input
            input_text = "summarize: " + text
            
            # Tokenize
            inputs = self.tokenizer.encode(
                input_text,
                return_tensors="pt",
                max_length=512,
                truncation=True
            )
            
            # Generate summary
            outputs = self.model.generate(
                inputs,
                max_length=max_length,
                min_length=min_length,
                length_penalty=length_penalty,
                num_beams=num_beams,
                early_stopping=True
            )
            
            # Decode summary
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return summary
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def summarize_long_text(self, text, chunk_size=1000, max_length=150):
        """
        Summarize long text by chunking
        
        Args:
            text: Long text to summarize
            chunk_size: Size of each chunk
            max_length: Maximum length for each summary
            
        Returns:
            str: Combined summary
        """
        if not text:
            return ""
        
        # Split text into chunks
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        summaries = []
        for chunk in chunks:
            if len(chunk.strip()) > 50:  # Only summarize meaningful chunks
                summary = self.summarize(chunk, max_length=max_length)
                summaries.append(summary)
        
        # Combine summaries
        combined_summary = " ".join(summaries)
        
        # If combined summary is still too long, summarize again
        if len(combined_summary) > 2000:
            combined_summary = self.summarize(combined_summary, max_length=max_length*2)
        
        return combined_summary
    
    def multi_level_summarize(self, text):
        """
        Generate multi-level summaries (brief, detailed, executive)
        
        Args:
            text: Text to summarize
            
        Returns:
            dict: Dictionary with different summary levels
        """
        summaries = {}
        
        # Brief summary (50-100 tokens)
        summaries['brief'] = self.summarize(
            text, 
            max_length=100, 
            min_length=30,
            num_beams=2
        )
        
        # Detailed summary (100-200 tokens)
        summaries['detailed'] = self.summarize(
            text,
            max_length=200,
            min_length=80,
            num_beams=4
        )
        
        # Executive summary (30-60 tokens)
        summaries['executive'] = self.summarize(
            text,
            max_length=60,
            min_length=20,
            num_beams=2
        )
        
        return summaries
    
    def batch_summarize(self, texts, max_length=150):
        """
        Summarize multiple texts
        
        Args:
            texts: List or dict of texts
            max_length: Maximum length for summaries
            
        Returns:
            dict: Dictionary of summaries
        """
        summaries = {}
        
        if isinstance(texts, dict):
            for key, text in texts.items():
                if isinstance(text, str) and len(text) > 100:
                    summaries[key] = self.summarize(text, max_length=max_length)
                else:
                    summaries[key] = text
        elif isinstance(texts, list):
            for i, text in enumerate(texts):
                if isinstance(text, str) and len(text) > 100:
                    summaries[f"text_{i}"] = self.summarize(text, max_length=max_length)
                else:
                    summaries[f"text_{i}"] = text
        
        return summaries


# Singleton instance for reuse
_summarizer_instance = None


def get_summarizer(model_name="t5-small"):
    """
    Get or create summarizer instance (singleton pattern)
    
    Args:
        model_name: Name of the T5 model
        
    Returns:
        TextSummarizer: Summarizer instance
    """
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = TextSummarizer(model_name)
    return _summarizer_instance


def summarize_framework(framework_text, level='detailed'):
    """
    Summarize a compliance framework
    
    Args:
        framework_text: Framework text to summarize
        level: Summary level (brief, detailed, executive)
        
    Returns:
        str: Framework summary
    """
    summarizer = get_summarizer()
    
    if level == 'multi':
        return summarizer.multi_level_summarize(framework_text)
    else:
        length_map = {
            'brief': (100, 30),
            'detailed': (200, 80),
            'executive': (60, 20)
        }
        max_len, min_len = length_map.get(level, (150, 50))
        return summarizer.summarize(framework_text, max_length=max_len, min_length=min_len)


def summarize_policy(policy_text):
    """
    Summarize an internal policy document
    
    Args:
        policy_text: Policy text to summarize
        
    Returns:
        str: Policy summary
    """
    summarizer = get_summarizer()
    
    if len(policy_text) > 2000:
        return summarizer.summarize_long_text(policy_text)
    else:
        return summarizer.summarize(policy_text)
