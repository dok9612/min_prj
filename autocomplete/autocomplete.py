from typing import List

def find_longest_common_prefix(strs: List[str]) -> str:
    if not strs:
        return ""
    
    for i in range(len(strs)):
        check_str = strs[0][i]
        
        for j in range(1, len(strs)):
            if i >= len(strs[j]) or strs[j][i] != check_str:
                return strs[0][:i]
            
    return strs[0]

    