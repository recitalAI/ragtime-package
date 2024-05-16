#!/usr/bin/env python3

from enum import IntEnum
class StartFrom(IntEnum):
	beginning = 0
	chunks = 1
	prompt = 2
	llm = 3
	post_process = 4
