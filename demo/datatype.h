/**
 * @file datatype.h
 * @author canrad (1517807724@qq.com)
 * @brief 基础类型的定义
 * 位，字节，字节序相关的操作
 * @version 0.2
 * @date 2025-07-21
 * @update
 * 2026-01-31 第一次明确datatype的类型标准
 *
 * @copyright Copyright (c) 2025
 *
 */
#ifndef LIBCA_EM_BASE_DATATYPE_H
#define LIBCA_EM_BASE_DATATYPE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/**
 * @brief 自动探测 64 位支持
 * 1. 尝试利用 UINTPTR_MAX 判断指针能否容纳 64 位 (原生 64 位环境)
 * 2. 尝试利用 UINT64_MAX 判断编译器是否支持 uint64_t (如 32 位机上的 long long)
 */
#ifndef HAS_INT64
    #if defined(UINTPTR_MAX) && (UINTPTR_MAX > 0xFFFFFFFFU)
        #define HAS_INT64 1
    #elif defined(UINT64_MAX)
        #define HAS_INT64 1
    #endif
#endif

// 整数
typedef uint8_t      u8;
typedef uint16_t     u16;
typedef uint32_t     u32;
typedef int8_t       i8;
typedef int16_t      i16;
typedef int32_t      i32;
#ifdef HAS_INT64
typedef uint64_t     u64;
typedef int64_t      i64;
#endif
// 浮点数
typedef float        f32;
typedef double       f64;
// size
typedef size_t          usize;

// 获取数组元素个数
#define array_size(arr) (sizeof(arr) / sizeof((arr)[0]))

// 判断一个变量是否为无符号类型
#define is_unsigned_v(a) (a >= 0 && ~a >= 0)

// 判断一个类型是否为无符号类型
#define is_unsigned_t(type) ((type)-1 > (type)0)

// 标记未使用的参数
// 例: unused_param(a);
#define unused_param(param) (void)(param)

#endif   // !LIBCA_EM_BASE_DATATYPE_H
