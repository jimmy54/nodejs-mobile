// Copyright 2016 the V8 project authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef V8_INSPECTOR_STRING_16_H_
#define V8_INSPECTOR_STRING_16_H_

#include <stdint.h>

#include <cctype>
#include <climits>
#include <cstring>
#include <string>
#include <vector>

// Fix for libc++ on Mac which removed char_traits<unsigned short>
namespace std {
template <>
struct char_traits<uint16_t> {
  using char_type = uint16_t;
  using int_type = int;
  using off_type = streamoff;
  using pos_type = streampos;
  using state_type = mbstate_t;

  static void assign(char_type& c1, const char_type& c2) noexcept { c1 = c2; }
  static bool eq(char_type c1, char_type c2) noexcept { return c1 == c2; }
  static bool lt(char_type c1, char_type c2) noexcept { return c1 < c2; }

  static int compare(const char_type* s1, const char_type* s2, size_t n) {
    while (n--) {
      if (*s1 < *s2) return -1;
      if (*s1 > *s2) return 1;
      ++s1;
      ++s2;
    }
    return 0;
  }

  static size_t length(const char_type* s) {
    const char_type* p = s;
    while (*p) ++p;
    return p - s;
  }

  static const char_type* find(const char_type* s, size_t n, const char_type& a) {
    while (n--) {
      if (*s == a) return s;
      ++s;
    }
    return nullptr;
  }

  static char_type* move(char_type* s1, const char_type* s2, size_t n) {
    return static_cast<char_type*>(std::memmove(s1, s2, n * sizeof(char_type)));
  }

  static char_type* copy(char_type* s1, const char_type* s2, size_t n) {
    return static_cast<char_type*>(std::memcpy(s1, s2, n * sizeof(char_type)));
  }

  static char_type* assign(char_type* s, size_t n, char_type a) {
    char_type* p = s;
    while (n--) *p++ = a;
    return s;
  }

  static int_type not_eof(int_type c) noexcept {
    return eq_int_type(c, eof()) ? ~eof() : c;
  }

  static char_type to_char_type(int_type c) noexcept {
    return static_cast<char_type>(c);
  }

  static int_type to_int_type(char_type c) noexcept {
    return static_cast<int_type>(c);
  }

  static bool eq_int_type(int_type c1, int_type c2) noexcept {
    return c1 == c2;
  }

  static int_type eof() noexcept { return static_cast<int_type>(-1); }
};
}  // namespace std

#include "src/base/compiler-specific.h"

namespace v8_inspector {

using UChar = uint16_t;

class String16 {
 public:
  static const size_t kNotFound = static_cast<size_t>(-1);

  String16() = default;
  String16(const String16&) V8_NOEXCEPT = default;
  String16(String16&&) V8_NOEXCEPT = default;
  String16(const UChar* characters, size_t size);
  V8_EXPORT String16(const UChar* characters);
  V8_EXPORT String16(const char* characters);
  String16(const char* characters, size_t size);
  explicit String16(const std::basic_string<UChar>& impl);
  explicit String16(std::basic_string<UChar>&& impl);

  String16& operator=(const String16&) V8_NOEXCEPT = default;
  String16& operator=(String16&&) V8_NOEXCEPT = default;

  static String16 fromInteger(int);
  static String16 fromInteger(size_t);
  static String16 fromInteger64(int64_t);
  static String16 fromUInt64(uint64_t);
  static String16 fromDouble(double);
  static String16 fromDouble(double, int precision);

  int64_t toInteger64(bool* ok = nullptr) const;
  uint64_t toUInt64(bool* ok = nullptr) const;
  int toInteger(bool* ok = nullptr) const;
  String16 stripWhiteSpace() const;
  const UChar* characters16() const { return m_impl.c_str(); }
  size_t length() const { return m_impl.length(); }
  bool isEmpty() const { return !m_impl.length(); }
  UChar operator[](size_t index) const { return m_impl[index]; }
  String16 substring(size_t pos, size_t len = UINT_MAX) const {
    return String16(m_impl.substr(pos, len));
  }
  size_t find(const String16& str, size_t start = 0) const {
    return m_impl.find(str.m_impl, start);
  }
  size_t reverseFind(const String16& str, size_t start = UINT_MAX) const {
    return m_impl.rfind(str.m_impl, start);
  }
  size_t find(UChar c, size_t start = 0) const { return m_impl.find(c, start); }
  size_t reverseFind(UChar c, size_t start = UINT_MAX) const {
    return m_impl.rfind(c, start);
  }
  void swap(String16& other) {
    m_impl.swap(other.m_impl);
    std::swap(hash_code, other.hash_code);
  }

  // Convenience methods.
  V8_EXPORT std::string utf8() const;
  V8_EXPORT static String16 fromUTF8(const char* stringStart, size_t length);

  // Instantiates a String16 in native endianness from UTF16 LE.
  // On Big endian architectures, byte order needs to be flipped.
  V8_EXPORT static String16 fromUTF16LE(const UChar* stringStart,
                                        size_t length);

  std::size_t hash() const {
    if (!hash_code) {
      for (char c : m_impl) hash_code = 31 * hash_code + c;
      // Map hash code 0 to 1. This double the number of hash collisions for 1,
      // but avoids recomputing the hash code.
      if (!hash_code) ++hash_code;
    }
    return hash_code;
  }

  inline bool operator==(const String16& other) const {
    return m_impl == other.m_impl;
  }
  inline bool operator<(const String16& other) const {
    return m_impl < other.m_impl;
  }
  inline bool operator!=(const String16& other) const {
    return m_impl != other.m_impl;
  }
  inline String16 operator+(const String16& other) const {
    return String16(m_impl + other.m_impl);
  }
  inline String16& operator+=(const String16& other) {
    m_impl += other.m_impl;
    return *this;
  }

  // Defined later, since it uses the String16Builder.
  template <typename... T>
  static String16 concat(T... args);

 private:
  std::basic_string<UChar> m_impl;
  mutable std::size_t hash_code = 0;
};

inline String16 operator+(const char* a, const String16& b) {
  return String16(a) + b;
}

class String16Builder {
 public:
  String16Builder();
  void append(const String16&);
  void append(UChar);
  void append(char);
  void append(const UChar*, size_t);
  void append(const char*, size_t);
  void appendNumber(int);
  void appendNumber(size_t);
  void appendUnsignedAsHex(uint64_t);
  void appendUnsignedAsHex(uint32_t);
  void appendUnsignedAsHex(uint8_t);
  String16 toString();
  void reserveCapacity(size_t);

  template <typename T, typename... R>
  void appendAll(T first, R... rest) {
    append(first);
    appendAll(rest...);
  }
  void appendAll() {}

 private:
  std::vector<UChar> m_buffer;
};

template <typename... T>
String16 String16::concat(T... args) {
  String16Builder builder;
  builder.appendAll(args...);
  return builder.toString();
}

}  // namespace v8_inspector

#if !defined(__APPLE__) || defined(_LIBCPP_VERSION)

namespace std {
template <>
struct hash<v8_inspector::String16> {
  std::size_t operator()(const v8_inspector::String16& string) const {
    return string.hash();
  }
};

}  // namespace std

#endif  // !defined(__APPLE__) || defined(_LIBCPP_VERSION)

#endif  // V8_INSPECTOR_STRING_16_H_
