import csv
import io

class CSVExtractor:
    def extract(self, file_bytes: bytes) -> list[dict]:
        """
        Extracts text from CSV files.
        Treats the whole CSV as a single 'page' or splits by row count if very large.
        Returns a list of dicts with 'page_number' and 'text'.
        """
        try:
            content = file_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            content = file_bytes.decode('latin-1', errors='replace')
            
        reader = csv.reader(io.StringIO(content))
        
        rows = []
        for row in reader:
            if any(cell.strip() for cell in row):
                rows.append(" | ".join(row))
                
        if not rows:
            return []
            
        return [{
            "page_number": 1,
            "text": "\n".join(rows)
        }]
