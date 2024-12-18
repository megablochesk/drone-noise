NUMBER_OF_ROWS = 1000
NUMBER_OF_COLUMNS = 1000


class Cell:
    def __init__(self, column_index, row_index, left_top_coordinate):
        self.column_index = column_index
        self.row_index = row_index
        self.left_top_coordinate = left_top_coordinate


class NoiseMatrix:
    def __init__(self):
        self.left_border = MAP_LEFT
        self.right_border = MAP_RIGHT
        self.top_border = MAP_TOP
        self.bottom_border = MAP_BOTTOM

        self.number_of_rows = NUMBER_OF_ROWS
        self.number_of_columns = NUMBER_OF_COLUMNS

        self.column_cell_size = abs(self.left_border - self.right_border) / self.number_of_columns
        self.row_cell_size = abs(self.top_border - self.bottom_border) / self.number_of_rows

    def get_left_top_corner_of_cell(self, column_index, row_index):
        if is_cell_index_valid(column_index, row_index):
            left_border_cell_coordinate = self.left_border + column_index * self.column_cell_size
            top_border_cell_coordinate = self.top_border + row_index * self.row_cell_size

            return left_border_cell_coordinate, top_border_cell_coordinate
        else:
            return None

    def _initialize_cells(self):
        cells = np.empty((self.number_of_rows, self.number_of_columns), dtype=object)
        for row_index in range(self.number_of_rows):
            for column_index in range(self.number_of_columns):
                left_top_coordinate = self.get_left_top_corner_of_cell(column_index, row_index)
                cells[row_index, column_index] = Cell(column_index, row_index, left_top_coordinate)
        return cells

    @staticmethod
    def is_index_valid(index, max_value):
        return isinstance(index, int) and 0 <= index < max_value

    def is_cell_index_valid(self, column_index, row_index):
        return (self.is_index_valid(column_index, self.number_of_columns) and
                self.is_index_valid(row_index, self.number_of_rows))

