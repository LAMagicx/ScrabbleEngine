"""
    This will be a functional scrabble implementation.
    
    All public functions will use the GCP format for inputs and outputs.
    Example:
        '13L1/12SO1/11FEW1/11AE2/11INK1/11L1I1/6CITE1E1T1/7NOTED1T1/13Y1/15/15/15/15/15/15 IRUSNPV/OIURAMU/AEZIUNA 38/38/45'
"""

def display_board(gcp: str) -> None:
    board, *_ = gcp.split(' ')
    output = ""
    idx = 0
    while idx < len(board):
        if board[idx] == '/':
            output += '\n'
        if board[idx].isdigit():
            if idx + 1 < len(board) and board[idx + 1].isdigit():
                count = int(board[idx: idx + 2])
                idx += 1
            else:
                count = int(board[idx])
            for _ in range(count):
                output += '. '
        if board[idx].isalpha():
            output += board[idx] + ' '
        idx += 1

    print(output)





def run_tests():
    example_gcp = '13L1/12SO1/11FEW1/11AE2/11INK1/11L1I1/6CITE1E1T1/7NOTED1T1/13Y1/15/15/15/15/15/15 IRUSNPV/OIURAMU/AEZIUNA 38/38/45'

    display_board(example_gcp)


if __name__ == "__main__":
    run_tests()
